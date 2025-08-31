from __future__ import annotations

import os
import csv
import json
import logging
import tempfile
import uuid
import zipfile
import io
from pathlib import Path
from datetime import datetime
from typing import Any, Iterable

import pandas as pd
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from dotenv import load_dotenv

from nicegui import ui, app
from nicegui.events import UploadEventArguments, TableSelectionEventArguments
from fastapi.responses import JSONResponse, StreamingResponse

# ---------------------------------------------------------------------------
# Environment & paths
BASE_DIR = Path(__file__).parent.resolve()
ASSETS_DIR = BASE_DIR / 'assets'
DOWNLOAD_DIR = BASE_DIR / 'downloads'
DOWNLOAD_DIR.mkdir(exist_ok=True)

load_dotenv()
VOICE_PROVIDER = os.getenv('VOICE_PROVIDER', 'offline').lower()
XI_API_KEY = os.getenv('XI_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
BASE_PUBLIC_URL = os.getenv('BASE_PUBLIC_URL', 'http://localhost:8080')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# serve downloads statically
app.add_static_files('/downloads', str(DOWNLOAD_DIR))

# ---------------------------------------------------------------------------
# Utility helpers


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def make_qr(url: str, out_png: Path) -> None:
    img = qrcode.make(url)
    ensure_dir(out_png.parent)
    img.save(out_png)


def simple_pdf(text: str, out_pdf: Path, qr_png: Path | None = None) -> None:
    ensure_dir(out_pdf.parent)
    c = canvas.Canvas(str(out_pdf), pagesize=LETTER)
    c.setFont('Helvetica', 14)
    c.drawString(72, 720, text)
    if qr_png and qr_png.exists():
        c.drawImage(str(qr_png), 450, 50, width=120, height=120,
                    preserveAspectRatio=True, mask='auto')
    c.showPage()
    c.save()

def zip_dir(src: Path, zip_path: Path) -> None:
    ensure_dir(zip_path.parent)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in src.rglob('*'):
            if p.is_file():
                z.write(p, p.relative_to(src))

def zip_dir(src: Path, zip_path: Path) -> None:
    ensure_dir(zip_path.parent)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in src.rglob('*'):
            if p.is_file():
                z.write(p, p.relative_to(src))

# ---------------------------------------------------------------------------
# Data model in memory

ORDERS: list[dict[str, Any]] = []
DOWNLOADS: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Parsing

COL_ALIASES = {
    'created': ['created', 'fecha'],
    'order': ['order', 'order_number', 'pedido'],
    'client': ['client', 'cliente', 'name'],
    'email': ['email', 'correo'],
    'cover': ['cover'],
    'size': ['size', 'tamaño'],
    'pages': ['pages', 'paginas'],
    'tags': ['tags'],
    'voice_name': ['voice_name', 'voice'],
    'voice_seed': ['voice_seed', 'voice_id'],
    'voice_text': ['voice_text', 'text'],
    'voice_sample': ['voice_sample', 'voice_clone', 'voice_file'],
}


def _val(data: dict, names: Iterable[str]) -> Any:
    for n in names:
        if n in data and pd.notna(data[n]):
            return data[n]
    return None


def parse_orders(temp_path: Path) -> list[dict]:
    if temp_path.suffix.lower() in {'.xlsx', '.xls'}:
        df = pd.read_excel(temp_path)
    else:
        try:
            df = pd.read_csv(temp_path, encoding='utf-8-sig')
        except Exception:
            df = pd.read_csv(temp_path, encoding='latin1')
    rows: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        data = r.to_dict()
        row = {
            'id': str(uuid.uuid4()),
            'created': str(_val(data, COL_ALIASES['created']) or datetime.now().date()),
            'order': str(_val(data, COL_ALIASES['order']) or ''),
            'client': str(_val(data, COL_ALIASES['client']) or ''),
            'email': str(_val(data, COL_ALIASES['email']) or ''),
            'cover': str(_val(data, COL_ALIASES['cover']) or ''),
            'size': str(_val(data, COL_ALIASES['size']) or ''),
            'pages': int(_val(data, COL_ALIASES['pages']) or 0),
            'status': 'pending',
            'tags': [t.strip() for t in str(_val(data, COL_ALIASES['tags']) or '').split(',') if t.strip()],
            'voice_name': str(_val(data, COL_ALIASES['voice_name']) or ''),
            'voice_seed': str(_val(data, COL_ALIASES['voice_seed']) or ''),
            'voice_text': str(_val(data, COL_ALIASES['voice_text']) or ''),
            'voice_sample': str(_val(data, COL_ALIASES['voice_sample']) or ''),
        }
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Audio synthesis


def synth_voice(row: dict, out_dir: Path) -> Path | None:
    if 'voice' not in row.get('tags', []) or not row.get('voice_text'):
        return None
    ensure_dir(out_dir)
    out_path = out_dir / 'voice.mp3'
    text = row['voice_text']
    provider = VOICE_PROVIDER
    try:
        if row.get('voice_sample'):
            try:
                from TTS.api import TTS  # type: ignore
                tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
                tts.tts_to_file(
                    text=text,
                    speaker_wav=row['voice_sample'],
                    language="es",
                    file_path=str(out_path),
                )
                return out_path
            except Exception as e:
                logger.warning('TTS voice clone unavailable: %s', e)
        if provider == 'elevenlabs' and XI_API_KEY:
            import requests
            voice_id = row.get('voice_seed') or '21m00Tcm4TlvDq8ikWAM'
            url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
            headers = {'xi-api-key': XI_API_KEY}
            payload = {'text': text, 'voice_settings': {'stability': 0.3, 'similarity_boost': 0.8}}
            r = requests.post(url, headers=headers, json=payload)
            if r.status_code != 200:
                raise RuntimeError(r.text)
            out_path.write_bytes(r.content)
            return out_path
        if provider == 'openai' and OPENAI_API_KEY:
            import requests
            voice = row.get('voice_name') or 'alloy'
            url = 'https://api.openai.com/v1/audio/speech'
            headers = {'Authorization': f'Bearer {OPENAI_API_KEY}'}
            payload = {'model': 'tts-1', 'input': text, 'voice': voice}
            r = requests.post(url, headers=headers, json=payload)
            if r.status_code != 200:
                raise RuntimeError(r.text)
            out_path.write_bytes(r.content)
            return out_path
        import pyttsx3
        engine = pyttsx3.init()
        engine.save_to_file(text, str(out_path))
        engine.runAndWait()
        return out_path
    except Exception as e:
        logger.error('voice synth failed: %s', e)
        return None


# ---------------------------------------------------------------------------
# Bundle generation


def generate_order_bundle(row: dict, base_out: Path) -> tuple[Path, Path]:
    work_dir = ensure_dir(base_out / f"order_{row['order']}_{row['id']}")
    docs_dir = ensure_dir(work_dir / 'docs')
    qr_dir = work_dir / 'qr'
    audio_dir = work_dir / 'audio'

    audio_rel = None
    audio_file = audio_dir / 'voice.mp3'
    if audio_file.exists():
        audio_rel = Path('audio/voice.mp3')

    qr_png = None
    if 'qr' in row.get('tags', []) or 'qr_audio' in row.get('tags', []):
        qr_url = f'{BASE_PUBLIC_URL}/o/{row["order"]}'
        if 'qr_audio' in row.get('tags', []) and audio_rel:
            qr_url = f'{BASE_PUBLIC_URL}/downloads/{work_dir.name}/{audio_rel.as_posix()}'
        qr_png = qr_dir / 'qr.png'
        make_qr(qr_url, qr_png)

    cover_pdf = docs_dir / 'cover.pdf'
    interior_pdf = docs_dir / 'interior.pdf'
    simple_pdf(f"Cover {row['order']} - {row['client']}", cover_pdf, qr_png)
    simple_pdf(f"Interior {row['order']} - {row['client']}", interior_pdf)

    manifest = dict(row)
    manifest.update({
        'generated_at': datetime.now().isoformat(),
        'docs': {'cover': 'docs/cover.pdf', 'interior': 'docs/interior.pdf'},
        'qr': 'qr/qr.png' if qr_png else None,
        'audio': str(audio_rel) if audio_rel else None,
    })
    (work_dir / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

    zip_path = base_out / f"order_{row['order']}.zip"
    zip_dir(work_dir, zip_path)
    return work_dir, zip_path


# ---------------------------------------------------------------------------
# API endpoints


@app.get('/api/import')
def api_import(temp_path: str):
    try:
        rows = parse_orders(Path(temp_path))
        ORDERS.extend(rows)
        return {'rows': rows}
    except Exception as e:
        logger.exception('import failed')
        return JSONResponse({'error': str(e)}, status_code=400)
@app.get('/api/export.csv')
def api_export_csv() -> StreamingResponse:
    def gen():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['id', 'created', 'order', 'client', 'email', 'cover', 'size', 'pages',
                         'status', 'tags', 'voice_name', 'voice_seed', 'voice_text'])
        for r in ORDERS:
            writer.writerow([
                r['id'], r['created'], r['order'], r['client'], r['email'], r['cover'],
                r['size'], r['pages'], r['status'], ','.join(r['tags']),
                r['voice_name'], r['voice_seed'], r['voice_text'],
            ])
        yield output.getvalue()
    headers = {'Content-Disposition': 'attachment; filename="orders.csv"'}
    return StreamingResponse(gen(), media_type='text/csv', headers=headers)


# ---------------------------------------------------------------------------
# UI

selected_ids: list[str] = []
table: ui.table
download_container: ui.column


def refresh_table() -> None:
    table.rows = ORDERS
    table.update()

async def handle_upload(e: UploadEventArguments) -> None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(e.name).suffix) as tmp:
        tmp.write(e.content.read())
        temp_path = Path(tmp.name)
    from fastapi.testclient import TestClient
    client = TestClient(app)
    res = client.get('/api/import', params={'temp_path': str(temp_path)})
    data = res.json()
    if res.status_code != 200 or 'error' in data:
        ui.notify(f"Error importando: {data.get('error', 'desconocido')}", type='negative')
        return
    ui.notify(f"{len(data['rows'])} filas importadas")
    refresh_table()

def import_block() -> None:
    with ui.card().classes('p-4'):
        ui.label('Importar pedidos (CSV/Excel)')
        ui.upload(on_upload=handle_upload, auto_upload=True).props('accept=.csv,.xlsx,.xls')


def load_sample_orders() -> None:
    samples = [
        {'order': '1001', 'client': 'Ana', 'email': 'ana@example.com', 'pages': 12, 'size': '7x10 espiral',
         'tags': ['qr', 'voice', 'qr_audio'], 'voice_name': 'Luz',
         'voice_text': 'Hola, este es tu audiolibro...'},
        {'order': '1002', 'client': 'Ben', 'email': 'ben@example.com', 'pages': 20, 'size': '8x8 hardcover',
         'tags': ['voice'], 'voice_name': 'Carlos', 'voice_text': 'Este es un mensaje sin QR.'},
        {'order': '1003', 'client': 'Carla', 'email': 'carla@example.com', 'pages': 32, 'size': '5x8 paperback',
         'tags': ['qr']},
        {'order': '1004', 'client': 'Diego', 'email': '', 'pages': 40, 'size': '7x10 espiral',
         'tags': ['voice'], 'voice_name': 'Elena', 'voice_text': 'Mensaje para libro sin email'},
        {'order': '1005', 'client': 'Eva', 'email': 'eva@example.com', 'pages': 64, 'size': '8x8 hardcover',
         'tags': ['qr_audio', 'voice'], 'voice_name': 'Mario', 'voice_seed': 'abc123',
         'voice_text': 'Mensaje con voice_seed y qr_audio'},
        {'order': '1006', 'client': 'José Ñandú', 'email': 'jose@example.com', 'pages': 20, 'size': '5x8 paperback',
         'tags': ['qr', 'voice'], 'voice_text': 'Nombre con caracteres raros'},
        {'order': '1007', 'client': 'Luisa', 'email': 'luisa@example.com', 'pages': 12, 'size': '7x10 espiral',
         'tags': []},
        {'order': '1008', 'client': 'Miguel', 'email': 'miguel@example.com', 'pages': 32, 'size': '8x8 hardcover',
         'tags': ['voice'], 'voice_text': 'Este es un texto de prueba largo para comprobar la duración del audio generado. Incluye varias frases y pausas para simular un párrafo completo.'},
        {'order': '1009', 'client': 'Nora', 'email': 'nora@example.com', 'pages': 40, 'size': '5x8 paperback',
         'tags': ['qr']},
        {'order': '1010', 'client': 'Oscar', 'email': 'oscar@example.com', 'pages': 64, 'size': '7x10 espiral',
         'tags': ['qr', 'voice'], 'voice_name': 'Luz', 'voice_text': 'Mensaje final'},
    ]
    for s in samples:
        s.setdefault('voice_name', '')
        s.setdefault('voice_seed', '')
        s.setdefault('voice_text', '')
        s['id'] = str(uuid.uuid4())
        s['created'] = str(datetime.now().date())
        s['status'] = 'pending'
    ORDERS.extend(samples)
    refresh_table()


async def generate_selected() -> None:
    rows = [r for r in ORDERS if r['id'] in selected_ids]
    if not rows:
        ui.notify('No hay pedidos seleccionados')
        return
    progress = ui.linear_progress(value=0.0)
    DOWNLOADS.clear()
    total = len(rows)
    for i, row in enumerate(rows, 1):
        try:
            audio_dir = DOWNLOAD_DIR / f"order_{row['order']}_{row['id']}" / 'audio'
            audio_path = synth_voice(row, audio_dir)
            work_dir, zip_path = generate_order_bundle(row, DOWNLOAD_DIR)
            row['status'] = 'ready'
            DOWNLOADS.append({'order': row['order'], 'zip': zip_path, 'dir': work_dir, 'audio': audio_path})
        except Exception as e:
            row['status'] = 'error'
            row['error'] = str(e)
            logger.exception('generation failed for %s', row['order'])
        progress.value = i / total
        refresh_table()
    progress.visible = False
    render_downloads()
    ui.notify('Generación completa')


def render_downloads() -> None:
    download_container.clear()
    if not DOWNLOADS:
        return
    with download_container:
        ui.label('Descargas').classes('text-lg')
        for d in DOWNLOADS:
            path = Path(d['zip']).name
            folder = Path(d['dir']).name if d.get('dir') else ''
            with ui.row():
                ui.label(f"Pedido {d['order']}")
                ui.button('Descargar ZIP', on_click=lambda p=path: ui.download(f'/downloads/{p}'))
                if folder:
                    ui.link('Ver cover', f'/downloads/{folder}/docs/cover.pdf', new_tab=True)
                    ui.link('Ver interior', f'/downloads/{folder}/docs/interior.pdf', new_tab=True)
                    if d.get('audio'):
                        ui.link('Escuchar audio', f'/downloads/{folder}/audio/voice.mp3', new_tab=True)
@ui.page('/')
def main_page() -> None:
    global table, download_container
    columns = [
        {'name': 'id', 'label': 'ID', 'field': 'id', 'sortable': False},
        {'name': 'order', 'label': 'Pedido', 'field': 'order'},
        {'name': 'client', 'label': 'Cliente', 'field': 'client'},
        {'name': 'email', 'label': 'Email', 'field': 'email'},
        {'name': 'pages', 'label': 'Páginas', 'field': 'pages'},
        {'name': 'size', 'label': 'Tamaño', 'field': 'size'},
        {'name': 'status', 'label': 'Status', 'field': 'status'},
    ]

    def on_select(e: TableSelectionEventArguments) -> None:
        selected_ids[:] = [r['id'] for r in e.selection]

    with ui.header().classes('items-center justify-between'):
        with ui.row():
            ui.button('GENERAR SELECCIONADOS', on_click=generate_selected)
            ui.button('EXPORTAR CSV', on_click=lambda: ui.download('/api/export.csv'))
            ui.button('REFRESCAR', on_click=refresh_table)
            ui.button('Cargar pedidos de prueba', on_click=load_sample_orders)

    table = ui.table(columns=columns, rows=ORDERS, row_key='id', selection='multiple', on_select=on_select)

    import_block()
    download_container = ui.column()


# ---------------------------------------------------------------------------
# Run app

if __name__ in {'__main__', '__mp_main__'}:
    ui.run(host='0.0.0.0', port=8080, reload=False)

