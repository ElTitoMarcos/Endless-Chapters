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
import requests
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from dotenv import load_dotenv

from nicegui import ui, app
from nicegui.events import UploadEventArguments
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


def simple_pdf(texts: list[str], out_pdf: Path, qr_png: Path | None = None) -> None:
    ensure_dir(out_pdf.parent)
    c = canvas.Canvas(str(out_pdf), pagesize=LETTER)
    for i, text in enumerate(texts):
        c.setFont('Helvetica', 14)
        c.drawString(72, 720, text)
        if i == 0 and qr_png and qr_png.exists():
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
    'tags': ['tags'],
    'personalized_characters': ['personalized_characters', 'characters'],
    'narration': ['narration'],
    'revisions': ['revisions', 'revision'],
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


def pages_for_cover(cover: str) -> int:
    cover_l = cover.lower()
    if cover_l == 'standard hardcover':
        return 12
    if cover_l == 'premium hardcover':
        return 24
    return 0


def books_for_cover(cover: str) -> int:
    return 2 if cover.lower() == 'premium hardcover' else 1


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
            'status': 'Pending to prompt',
            'tags': [t.strip() for t in str(_val(data, COL_ALIASES['tags']) or '').split(',') if t.strip()],
            'personalized_characters': int(_val(data, COL_ALIASES['personalized_characters']) or 0),
            'narration': str(_val(data, COL_ALIASES['narration']) or ''),
            'revisions': int(_val(data, COL_ALIASES['revisions']) or 0),
            'voice_name': str(_val(data, COL_ALIASES['voice_name']) or ''),
            'voice_seed': str(_val(data, COL_ALIASES['voice_seed']) or ''),
            'voice_text': str(_val(data, COL_ALIASES['voice_text']) or ''),
            'voice_sample': str(_val(data, COL_ALIASES['voice_sample']) or ''),
        }
        row['pages'] = pages_for_cover(row['cover'])
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

    book_pdf = docs_dir / 'book.pdf'
    texts = [
        f"Cover {row['order']} - {row['client']}",
        f"Interior {row['order']} - {row['client']}",
    ]
    simple_pdf(texts, book_pdf, qr_png)

    manifest = dict(row)
    manifest.update({
        'generated_at': datetime.now().isoformat(),
        'docs': {'book': 'docs/book.pdf'},
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
        writer.writerow(['created', 'order', 'client', 'email', 'cover',
                         'personalized_characters', 'narration', 'revisions',
                         'status', 'tags', 'voice_name', 'voice_seed', 'voice_text'])
        for r in ORDERS:
            writer.writerow([
                r['created'], r['order'], r['client'], r['email'], r['cover'],
                r['personalized_characters'], r['narration'],
                r['revisions'], r['status'], ','.join(r['tags']),
                r['voice_name'], r['voice_seed'], r['voice_text'],
            ])
        yield output.getvalue()
    headers = {'Content-Disposition': 'attachment; filename="orders.csv"'}
    return StreamingResponse(gen(), media_type='text/csv', headers=headers)


# ---------------------------------------------------------------------------
# UI

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
        {'order': '1001', 'client': 'Ana', 'email': 'ana@example.com',
         'cover': 'Premium Hardcover', 'personalized_characters': 0,
         'narration': 'Narrated by your loved one', 'revisions': 0,
         'tags': ['qr', 'voice', 'qr_audio'], 'voice_name': 'Luz',
         'voice_text': 'Hola, este es tu audiolibro...'},
        {'order': '1002', 'client': 'Ben', 'email': 'ben@example.com',
         'cover': 'Standard Hardcover', 'personalized_characters': 1,
         'narration': 'None', 'revisions': 1,
         'tags': ['voice'], 'voice_name': 'Carlos', 'voice_text': 'Este es un mensaje sin QR.'},
        {'order': '1003', 'client': 'Carla', 'email': 'carla@example.com',
         'cover': 'Premium Hardcover', 'personalized_characters': 2,
         'narration': 'Narrated by your loved one', 'revisions': 2,
         'tags': ['qr']},
        {'order': '1004', 'client': 'Diego', 'email': '',
         'cover': 'Standard Hardcover', 'personalized_characters': 3,
         'narration': 'None', 'revisions': 3,
         'tags': ['voice'], 'voice_name': 'Elena', 'voice_text': 'Mensaje para libro sin email'},
        {'order': '1005', 'client': 'Eva', 'email': 'eva@example.com',
         'cover': 'Premium Hardcover', 'personalized_characters': 0,
         'narration': 'Narrated by your loved one', 'revisions': 1,
         'tags': ['qr_audio', 'voice'], 'voice_name': 'Mario', 'voice_seed': 'abc123',
         'voice_text': 'Mensaje con voice_seed y qr_audio'},
        {'order': '1006', 'client': 'José Ñandú', 'email': 'jose@example.com',
         'cover': 'Standard Hardcover', 'personalized_characters': 2,
         'narration': 'None', 'revisions': 0,
         'tags': ['qr', 'voice'], 'voice_text': 'Nombre con caracteres raros'},
        {'order': '1007', 'client': 'Luisa', 'email': 'luisa@example.com',
         'cover': 'Premium Hardcover', 'personalized_characters': 1,
         'narration': 'Narrated by your loved one', 'revisions': 2,
         'tags': []},
        {'order': '1008', 'client': 'Miguel', 'email': 'miguel@example.com',
         'cover': 'Standard Hardcover', 'personalized_characters': 0,
         'narration': 'None', 'revisions': 3,
         'tags': ['voice'], 'voice_text': 'Este es un texto de prueba largo para comprobar la duración del audio generado. Incluye varias frases y pausas para simular un párrafo completo.'},
        {'order': '1009', 'client': 'Nora', 'email': 'nora@example.com',
         'cover': 'Premium Hardcover', 'personalized_characters': 3,
         'narration': 'Narrated by your loved one', 'revisions': 0,
         'tags': ['qr']},
        {'order': '1010', 'client': 'Oscar', 'email': 'oscar@example.com',
         'cover': 'Standard Hardcover', 'personalized_characters': 1,
         'narration': 'None', 'revisions': 1,
         'tags': ['qr', 'voice'], 'voice_name': 'Luz', 'voice_text': 'Mensaje final'},
    ]
    for s in samples:
        s.setdefault('voice_name', '')
        s.setdefault('voice_seed', '')
        s.setdefault('voice_text', '')
        s.setdefault('personalized_characters', 0)
        s.setdefault('narration', 'None')
        s.setdefault('revisions', 0)
        s['id'] = str(uuid.uuid4())
        s['created'] = str(datetime.now().date())
        s['status'] = 'Pending to prompt'
        s['pages'] = pages_for_cover(s['cover'])
    ORDERS.extend(samples)
    refresh_table()


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
                    ui.link('Ver libro', f'/downloads/{folder}/docs/book.pdf', new_tab=True)
                    if d.get('audio'):
                        ui.audio(f'/downloads/{folder}/audio/voice.mp3').props('controls')


async def generate_prompt(row: dict) -> None:
    try:
        story_pages = 10
        num_books = books_for_cover(row.get('cover', ''))
        prompts: list[str] = []
        for i in range(num_books):
            content = ("Genera un prompt breve para " +
                       ("la continuación del cuento anterior " if i else "") +
                       f"de {story_pages} páginas para {row['client']}." )
            if OPENAI_API_KEY:
                payload = {
                    'model': 'gpt-4o-mini',
                    'messages': [{'role': 'user', 'content': content}],
                }
                headers = {'Authorization': f'Bearer {OPENAI_API_KEY}'}
                r = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
                prompts.append(data['choices'][0]['message']['content'])
            else:
                if i == 0:
                    prompts.append(f"Historia para {row['client']} de {story_pages} páginas (Libro 1).")
                else:
                    prompts.append(f"Historia continuación para {row['client']} de {story_pages} páginas (Libro {i+1}).")
        row['prompts'] = prompts
        row['status'] = 'Pending to upload file'
        refresh_table()
        ui.notify('Prompts generados')
    except Exception as e:
        ui.notify(f'Error generando prompts: {e}', type='negative')


async def open_storybook(row: dict) -> None:
    try:
        prompts = row.get('prompts') or []
        for p in prompts:
            ui.open('https://gemini.google.com/gem/storybook')
            await ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(p)});")
        audio_dir = DOWNLOAD_DIR / f"order_{row['order']}_{row['id']}" / 'audio'
        audio_path = synth_voice(row, audio_dir)
        work_dir, zip_path = generate_order_bundle(row, DOWNLOAD_DIR)
        row['status'] = 'Pending yo revise PDF'
        DOWNLOADS.append({'order': row['order'], 'zip': zip_path, 'dir': work_dir, 'audio': audio_path})
        refresh_table()
        render_downloads()
        ui.notify('Libro generado, revisa el PDF')
    except Exception as e:
        ui.notify(f'Error preparando libro: {e}', type='negative')


def mark_done(row: dict) -> None:
    row['status'] = 'DONE'
    refresh_table()
@ui.page('/')
def main_page() -> None:
    global table, download_container
    columns = [
        {'name': 'order', 'label': 'Pedido', 'field': 'order'},
        {'name': 'client', 'label': 'Cliente', 'field': 'client'},
        {'name': 'email', 'label': 'Email', 'field': 'email'},
        {'name': 'cover', 'label': 'Cubierta', 'field': 'cover'},
        {'name': 'personalized_characters', 'label': 'Personajes', 'field': 'personalized_characters'},
        {'name': 'narration', 'label': 'Narración', 'field': 'narration'},
        {'name': 'revisions', 'label': 'Revisiones', 'field': 'revisions'},
        {'name': 'status', 'label': 'Status', 'field': 'status'},
    ]

    with ui.header().classes('items-center justify-between'):
        with ui.row():
            ui.button('EXPORTAR CSV', on_click=lambda: ui.download('/api/export.csv'))
            ui.button('REFRESCAR', on_click=refresh_table)
            ui.button('Cargar pedidos de prueba', on_click=load_sample_orders)

    table = ui.table(columns=columns, rows=ORDERS, row_key='id')

    status_slot = """
    <q-td :props="props">
      <div class='row items-center q-gutter-sm'>
        <span>{{ props.row.status }}</span>
        <q-btn v-if="props.row.status === 'Pending to prompt'"
               label="Generar prompt"
               @click="() => emit('generate_prompt', props.row.id)"/>
        <q-btn v-else-if="props.row.status === 'Pending to upload file'"
               label="Abrir Storybook"
               @click="() => emit('open_storybook', props.row.id)"/>
        <q-btn v-else-if="props.row.status === 'Pending yo revise PDF'"
               label="Marcar DONE"
               @click="() => emit('mark_done', props.row.id)"/>
      </div>
    </q-td>
    """
    table.add_slot('body-cell-status', status_slot)

    def _row_from_event(e):
        rid = e.args if isinstance(e.args, str) else e.args[0]
        return next(r for r in ORDERS if r['id'] == rid)

    table.on('generate_prompt', lambda e: ui.run_async(generate_prompt(_row_from_event(e))))
    table.on('open_storybook', lambda e: ui.run_async(open_storybook(_row_from_event(e))))
    table.on('mark_done', lambda e: mark_done(_row_from_event(e)))
    import_block()
    download_container = ui.column()


# ---------------------------------------------------------------------------
# Run app

if __name__ in {'__main__', '__mp_main__'}:
    ui.run(host='0.0.0.0', port=8080, reload=False)

