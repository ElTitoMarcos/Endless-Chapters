from __future__ import annotations
from typing import Optional
import tempfile
import uuid
# -*- coding: utf-8 -*-
import os, io, json, uuid, sqlite3, shutil, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
from nicegui import ui, app, events
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import pikepdf

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
DOWNLOAD_DIR = BASE_DIR / "downloads"
DB_PATH = DATA_DIR / "app.db"

# -- montar descargas
try:
    already = any(isinstance(r, Mount) and getattr(r, 'path', None) == '/download' for r in app.routes)
except Exception:
    already = False
if not already:
    app.mount('/download', StaticFiles(directory=str(DOWNLOAD_DIR)), name='download')

def serve_path(path: Path, name: str) -> str:
    return f"/download/{name}"

# ------------------ SQLite helpers ------------------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
      id TEXT PRIMARY KEY,
      created_at TEXT,
      order_code TEXT,         -- id externo (del CSV/Excel)
      customer_name TEXT,
      email TEXT,
      cover_type TEXT,
      size TEXT,
      pages INTEGER,
      wants_qr INTEGER,
      wants_voice INTEGER,
      tags TEXT,               -- coma separada
      meta_json TEXT,          -- JSON completo de la fila
      status TEXT DEFAULT 'imported'
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS files (
      id TEXT PRIMARY KEY,
      order_id TEXT,
      kind TEXT,               -- 'voice' | 'pdf_a' | 'pdf_b' | 'processed_pdf' | 'prompt_txt'
      filename TEXT,
      path TEXT,
      created_at TEXT
    );
    """)
    conn.commit()
    conn.close()

def upsert_order(row: dict) -> str:
    """Inserta pedido si no existe (por order_code+email) y devuelve id interno."""
    conn = db()
    cur = conn.cursor()
    order_code = str(row.get('order_id') or row.get('order') or row.get('id') or row.get('Order') or row.get('ORDER') or '')
    email = str(row.get('email') or row.get('Email') or '')
    customer = str(row.get('customer') or row.get('Customer') or row.get('name') or row.get('Name') or '')
    cover = (row.get('cover_type') or row.get('cover') or row.get('Cover') or '').strip().lower()
    size = (row.get('size') or row.get('Size') or '').strip()
    try:
        pages = int(row.get('pages') or row.get('Pages') or 0)
    except Exception:
        pages = 0
    # detectar QR / voz por columnas o por tags
    tags_raw = row.get('tags') or row.get('Tags') or ''
    tags = str(tags_raw)
    tags_l = [t.strip().lower() for t in str(tags).split(',') if t.strip()]
    wants_qr = any(t in ('qr','qrcode','codigo qr','cï¿½digo qr') for t in tags_l) or bool(str(row.get('wants_qr') or row.get('qr') or 'false').strip().lower() in ('1','true','si','si','yes'))
    wants_voice = any(t in ('voz','narration','voice','voice_clone','clonar voz','narraciï¿½n') for t in tags_l) or bool(str(row.get('wants_voice') or row.get('voice') or 'false').strip().lower() in ('1','true','sï¿½','si','yes'))

    meta_json = json.dumps(row, ensure_ascii=False)
    oid = str(uuid.uuid4())

    # ï¿½duplicado por order_code+email?
    cur.execute("SELECT id FROM orders WHERE order_code=? AND COALESCE(email,'')=COALESCE(?, '')", (order_code, email))
    existing = cur.fetchone()
    if existing:
        oid = existing['id']
        cur.execute("""UPDATE orders SET customer_name=?, cover_type=?, size=?, pages=?, 
                       wants_qr=?, wants_voice=?, tags=?, meta_json=?, status=COALESCE(status,'imported')
                       WHERE id=?""",
                    (customer, cover, size, pages, int(wants_qr), int(wants_voice), tags, meta_json, oid))
    else:
        cur.execute("""INSERT INTO orders (id, created_at, order_code, customer_name, email, cover_type, size, pages, wants_qr, wants_voice, tags, meta_json, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'imported')""",
                    (oid, datetime.now(timezone.utc).isoformat(), order_code, customer, email, cover, size, pages, int(wants_qr), int(wants_voice), tags, meta_json))
    conn.commit()
    conn.close()
    return oid

def list_orders():
    conn = db()
    rows = conn.execute("SELECT * FROM orders ORDER BY datetime(created_at) DESC").fetchall()
    conn.close()
    return rows

def get_order(oid: str):
    conn = db()
    row = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    conn.close()
    return row

def has_voice(oid: str) -> bool:
    conn = db()
    r = conn.execute("SELECT 1 FROM files WHERE order_id=? AND kind='voice'", (oid,)).fetchone()
    conn.close()
    return bool(r)

def add_file(oid: str, kind: str, src_tmp: Path, final_name: str | None = None) -> Path:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = ''.join(Path(src_tmp.name).suffixes) or ''
    name = final_name or f"{oid}-{kind}{ext}"
    dest = DOWNLOAD_DIR / name
    shutil.move(str(src_tmp), str(dest))
    conn = db()
    conn.execute("INSERT INTO files (id, order_id, kind, filename, path, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                 (str(uuid.uuid4()), oid, kind, name, str(dest), datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()
    return dest

def files_for_order(oid: str, kind: str | None = None):
    conn = db()
    if kind:
        rows = conn.execute("SELECT * FROM files WHERE order_id=? AND kind=? ORDER BY datetime(created_at) DESC", (oid, kind)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM files WHERE order_id=? ORDER BY datetime(created_at) DESC", (oid,)).fetchall()
    conn.close()
    return rows

# ------------------ PDF helpers ------------------
def ghostscript_path() -> str | None:
    # intenta encontrar Ghostscript (para B/N)
    candidates = [
        r"C:\Program Files\gs\gs10.03.1\bin\gswin64c.exe",
        r"C:\Program Files\gs\gs10.02.1\bin\gswin64c.exe",
        r"C:\Program Files\gs\gs10.01.2\bin\gswin64c.exe",
        r"C:\Program Files\gs\gs9.55.0\bin\gswin64c.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    # si estï¿½ en PATH
    return "gswin64c" if shutil.which("gswin64c") else None

def grayscale_except_cover(src: Path, pages_cover: int, dst: Path) -> bool:
    """Devuelve True si se pudo B/N, False si se deja en color (por falta de GS)."""
    gs = ghostscript_path()
    if not gs:
        shutil.copyfile(src, dst)
        return False
    tmp_gray = src.with_suffix(".all_gray.pdf")
    # B/N completo con GS
    args = [
        gs, "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.5",
        "-dProcessColorModel=/DeviceGray", "-dColorConversionStrategy=/Gray",
        "-dAutoRotatePages=/None", "-dNOPAUSE", "-dBATCH",
        f"-sOutputFile={tmp_gray}", str(src)
    ]
    try:
        subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        shutil.copyfile(src, dst)
        return False
    # recombinar: primeras N pï¿½ginas en color del original + resto en gris
    with pikepdf.open(str(src)) as cpdf, pikepdf.open(str(tmp_gray)) as gpdf, pikepdf.new() as out:
        total = len(cpdf.pages)
        cov = min(pages_cover, total)
        for i in range(cov):
            out.pages.append(cpdf.pages[i])
        for i in range(cov, total):
            out.pages.append(gpdf.pages[i])
        out.save(str(dst))
    tmp_gray.unlink(missing_ok=True)
    return True

def add_qr_page(pdf_in: Path, qr_value: str, pdf_out: Path):
    # genera una ï¿½ltima pï¿½gina con un QR grande y texto
    qr_img = qrcode.make(qr_value)
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)

    tmp_qr = pdf_in.with_suffix(".qrpage.pdf")
    c = canvas.Canvas(str(tmp_qr), pagesize=A4)
    iw, ih = ImageReader(qr_buf).getSize()
    # escalar para que quepa agradablemente (~70% del ancho)
    page_w, page_h = A4
    target_w = page_w * 0.7
    scale = target_w / iw
    tw, th = iw * scale, ih * scale
    x = (page_w - tw) / 2
    y = (page_h - th) / 2 + 40
    c.drawImage(ImageReader(qr_buf), x, y, width=tw, height=th, mask='auto')
    c.setFont("Helvetica", 14)
    c.drawCentredString(page_w/2, y - 24, "Escanea este cï¿½digo para acceder al contenido de audio")
    c.save()

    with pikepdf.open(str(pdf_in)) as inp, pikepdf.open(str(tmp_qr)) as tail, pikepdf.new() as out:
        for p in inp.pages:
            out.pages.append(p)
        for p in tail.pages:
            out.pages.append(p)
        out.save(str(pdf_out))
    tmp_qr.unlink(missing_ok=True)

# ------------------ Prompts ------------------
PROMPT_BASE = """Quiero un cuento infantil personalizado.
Datos:
- Cliente: {customer}
- Tamaï¿½o: {size}
- Tipo de tapa: {cover}
- Pï¿½ginas: {pages}
- Tono: cï¿½lido, educativo y divertido.
Instrucciones:
- Escribe en escenas de 1 pï¿½gina cada una.
- Espaï¿½ol neutro, frases cortas, apto 4-7 aï¿½os.
- Evita violencia o miedo.
"""

PROMPT_VARIATIONS = [
    "Tema central: amistad y trabajo en equipo. Aï¿½ade un giro sorpresa al final.",
    "Tema central: aventura y descubrimiento. Incluye un acertijo sencillo a mitad del libro.",
    "Tema central: superaciï¿½n personal. Introduce un personaje ayudante con frase recurrente."
]

def make_prompts(order: sqlite3.Row) -> list[tuple[str, str]]:
    """Devuelve lista [(nombre, contenido_txt), ...]. Si 24p tapa dura -> doble prompt (A/B)."""
    prompts = []
    for i, v in enumerate(PROMPT_VARIATIONS, start=1):
        base = PROMPT_BASE + "\n" + v + "\n"
        if (order['cover_type'] or '').lower() == 'hardcover' and int(order['pages'] or 0) == 24:
            # dos mitades
            pa = base + "\nGenera la PARTE A (pï¿½ginas 1-12). Cierra en mini-cliffhanger amable."
            pb = base + "\nGenera la PARTE B (pï¿½ginas 13-24). Retoma y cierra la historia con moraleja."
            prompts.append((f"prompt_var{i}_parte_A.txt", pa))
            prompts.append((f"prompt_var{i}_parte_B.txt", pb))
        else:
            prompts.append((f"prompt_var{i}.txt", base))
    return prompts

# ------------------ UI ------------------
def header():
    with ui.header().classes('items-center justify-between'):
        ui.label('Endless Chapters Studio').classes('text-lg font-bold')
        with ui.row().classes('items-center gap-3'):
            ui.link('Descargas', '/download/', new_tab=True)
            ui.link('Repositorio de pedidos', '#pedidos')
def page_list_orders():
    import sqlite3
    from pathlib import Path

    def _db_path():
        try:
            return str(DB_PATH)
        except NameError:
            try:
                base = DATA_DIR
            except NameError:
                base = Path(__file__).parent / 'data'
                base.mkdir(parents=True, exist_ok=True)
            return str(base / 'app.db')

    def _fetch_orders(limit: int = 1000):
        conn = sqlite3.connect(_db_path())
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        base_cols = "id, created_at, order_code, customer_name, email, cover_type, size, pages, wants_qr, wants_voice"
        try:
            q = f"SELECT {base_cols}, COALESCE(status,'') AS status FROM orders ORDER BY created_at DESC LIMIT ?"
            rows = cur.execute(q, (limit,)).fetchall()
        except sqlite3.OperationalError:
            q = f"SELECT {base_cols} FROM orders ORDER BY created_at DESC LIMIT ?"
            rows = cur.execute(q, (limit,)).fetchall()
        out = [dict(r) for r in rows]
        conn.close()
        return out

    rows = _fetch_orders()
    if not rows:
        ui.label('Sin pedidos aún')
        return

    def to_row(r):
        return {
            'id': r.get('id'),
            'created': str(r.get('created_at','')).split('T')[0],
            'order': r.get('order_code',''),
            'cliente': r.get('customer_name',''),
            'email': r.get('email',''),
            'cover': r.get('cover_type',''),
            'size': r.get('size',''),
            'pages': r.get('pages',''),
            'qr': 'Sí' if r.get('wants_qr') else 'No',
            'voz': 'Sí' if r.get('wants_voice') else 'No',
            'estado': r.get('status',''),
        }

    ui.label('Pedidos').classes('text-xl font-bold mb-2')

    friendly_rows = [to_row(r) for r in rows]
    cols = [{'name': k, 'label': k.replace('_',' ').title(), 'field': k, 'sortable': True} for k in friendly_rows[0].keys()]
    t = ui.table(columns=cols, rows=friendly_rows, row_key='id').classes('w-full')



    def parse_orders(temp_path: Path):
        ext = temp_path.suffix.lower()
        try:
            if ext == '.csv':
                try:
                    df = pd.read_csv(temp_path, encoding='utf-8-sig')
                except Exception:
                    df = pd.read_csv(temp_path, encoding='latin1')
            else:
                df = pd.read_excel(temp_path)
        except Exception as e:
            ui.notify(f'Error leyendo archivo: {e}', color='negative')
            return 0
        n = 0
        for row in df.fillna('').to_dict('records'):
            try:
                upsert_order(row)
                n += 1
            except Exception as e:
                ui.notify(f'Fila con error: {e}', color='warning', timeout=6000)
        return n

    async def on_upload(e):
        # e no tipado (evita choque de versiones)
        up = e  # NiceGUI entrega .name, .content
        suffix = Path(up.name).suffix.lower()
        if suffix not in ('.csv', '.xlsx', '.xls'):
            ui.notify('Solo se aceptan .csv, .xlsx, .xls', color='warning')
            return
        tmp = DATA_DIR / f"upload-{uuid.uuid4()}{suffix}"
        with open(tmp, 'wb') as f:
            f.write(up.content.read())
        added = parse_orders(tmp)
        ui.notify(f'Importados: {added}', color='positive')
        ui.run_javascript('window.location.hash = "#pedidos"; window.location.reload()')

    ui.upload(label='Selecciona CSV/Excel', on_upload=on_upload).props('accept=.csv,.xlsx,.xls').classes('w-full')

def order_page(oid: str):
    r = get_order(oid)
    if not r:
        ui.label('Pedido no encontrado').classes('text-red-600')
        return
    wants_qr = bool(r['wants_qr'])
    wants_voice = bool(r['wants_voice'])
    pages = int(r['pages'] or 0)
    is_hd_24 = (r['cover_type'] or '').lower() == 'hardcover' and pages == 24

    ui.label(f"Pedido {r['order_code']}").classes('text-xl font-bold')
    ui.markdown(
        f"- Cliente: **{r['customer_name']}**  \n"
        f"- Email: **{r['email']}**  \n"
        f"- Tapa: **{r['cover_type']}** | Tamaï¿½o: **{r['size']}** | Pï¿½ginas: **{pages}**  \n"
        f"- Requiere QR: **{'Sï¿½' if wants_qr else 'No'}** | Requiere voz: **{'Sï¿½' if wants_voice else 'No'}**"
    )

    # ---- Voice (obligatoria si se requiere) ----
    if wants_voice and not has_voice(oid):
        ui.separator()
        ui.label('Este pedido requiere archivo de voz para clonaciï¿½n').classes('text-md text-amber-700')
        async def on_voice(e):
            up = e
            ext = Path(up.name).suffix.lower()
            if ext not in ('.wav', '.mp3', '.m4a', '.flac'):
                ui.notify('Sube .wav/.mp3/.m4a/.flac', color='warning'); return
            tmp = DATA_DIR / f"voice-{uuid.uuid4()}{ext}"
            with open(tmp, 'wb') as f: f.write(up.content.read())
            add_file(oid, 'voice', tmp, final_name=f"{oid}-voice{ext}")
            ui.notify('Voz cargada ?'); ui.run_javascript('window.location.reload()')
        ui.upload('Subir voz (obligatorio)', on_upload=on_voice).props('accept=.wav,.mp3,.m4a,.flac')

    # ---- Prompts (3 variaciones). Si 24p HD => doble prompt A/B ----
    ui.separator()
    ui.label('Prompts sugeridos').classes('text-md font-medium')
    def gen_and_save_prompts():
        for name, txt in make_prompts(r):
            p = DOWNLOAD_DIR / f"{oid}-{name}"
            with open(p, 'w', encoding='utf-8') as f: f.write(txt)
            conn = db(); conn.execute(
                "INSERT INTO files (id, order_id, kind, filename, path, created_at) VALUES (?, ?, 'prompt_txt', ?, ?, ?)",
                (str(uuid.uuid4()), oid, p.name, str(p), datetime.now(timezone.utc).isoformat())
            ); conn.commit(); conn.close()
        ui.notify('Prompts generados en Descargas', color='positive'); ui.run_javascript('window.location.reload()')

    ui.button('Generar 3 prompts', on_click=gen_and_save_prompts, color='primary')

    # Mostrar prompts (si existen)
    prompts = files_for_order(oid, 'prompt_txt')
    if prompts:
        with ui.column().classes('mt-2'):
            for f in prompts:
                ui.link(f['filename'], serve_path(Path(f['path']), f['filename']), new_tab=True)

    # ---- PDF(s) finales para procesar ----
    ui.separator()
    if is_hd_24:
        ui.label('Sube los 2 PDFs finales (Parte A y Parte B)').classes('text-md')
    else:
        ui.label('Sube el PDF final del libro').classes('text-md')

    needed_voices_ok = (not wants_voice) or has_voice(oid)

    async def on_pdf_a(e):
        up = e
        if Path(up.name).suffix.lower() != '.pdf':
            ui.notify('Solo PDF', color='warning'); return
        tmp = DATA_DIR / f"pdfA-{uuid.uuid4()}.pdf"
        with open(tmp, 'wb') as f: f.write(up.content.read())
        add_file(oid, 'pdf_a', tmp, final_name=f"{oid}-A.pdf")
        ui.notify('PDF A subido'); ui.run_javascript('window.location.reload()')

    async def on_pdf_b(e):
        up = e
        if Path(up.name).suffix.lower() != '.pdf':
            ui.notify('Solo PDF', color='warning'); return
        tmp = DATA_DIR / f"pdfB-{uuid.uuid4()}.pdf"
        with open(tmp, 'wb') as f: f.write(up.content.read())
        add_file(oid, 'pdf_b', tmp, final_name=f"{oid}-B.pdf")
        ui.notify('PDF B subido'); ui.run_javascript('window.location.reload()')

    async def on_pdf_single(e):
        up = e
        if Path(up.name).suffix.lower() != '.pdf':
            ui.notify('Solo PDF', color='warning'); return
        tmp = DATA_DIR / f"pdf-{uuid.uuid4()}.pdf"
        with open(tmp, 'wb') as f: f.write(up.content.read())
        add_file(oid, 'pdf_a', tmp, final_name=f"{oid}.pdf")  # reutilizamos slot A
        ui.notify('PDF subido'); ui.run_javascript('window.location.reload()')

    if is_hd_24:
        ui.upload('PDF Parte A (pï¿½gs. 1-12)', on_upload=on_pdf_a).props('accept=.pdf')
        ui.upload('PDF Parte B (pï¿½gs. 13-24)', on_upload=on_pdf_b).props('accept=.pdf')
    else:
        ui.upload('PDF final', on_upload=on_pdf_single).props('accept=.pdf')

    # botï¿½n procesar (sï¿½lo si requisitos cumplidos)
    def can_process():
        if not needed_voices_ok:
            return False, 'Falta archivo de voz'
        if is_hd_24:
            have_a = bool(files_for_order(oid, 'pdf_a'))
            have_b = bool(files_for_order(oid, 'pdf_b'))
            return (have_a and have_b), 'Sube A y B' if not (have_a and have_b) else ''
        else:
            have = bool(files_for_order(oid, 'pdf_a'))
            return have, 'Sube PDF'
    ok, msg = can_process()

    def run_pipeline():
        # input(s)
        if is_hd_24:
            fA = Path(files_for_order(oid, 'pdf_a')[0]['path'])
            fB = Path(files_for_order(oid, 'pdf_b')[0]['path'])
            merged = DATA_DIR / f"{oid}-merged.pdf"
            # unir A+B (sin cambios)
            with pikepdf.open(str(fA)) as A, pikepdf.open(str(fB)) as B, pikepdf.new() as out:
                for p in A.pages: out.pages.append(p)
                for p in B.pages: out.pages.append(p)
                out.save(str(merged))
            source_pdf = merged
            cover_pages = 1  # asumimos 1 portada
        else:
            source_pdf = Path(files_for_order(oid, 'pdf_a')[0]['path'])
            cover_pages = 1

        # B/N excepto portada
        gray_pdf = DATA_DIR / f"{oid}-gray.pdf"
        did_gray = grayscale_except_cover(source_pdf, cover_pages, gray_pdf)
        if not did_gray:
            ui.notify('Ghostscript no encontrado: PDF se mantiene en color', color='warning', timeout=6000)

        # QR si procede
        final_pdf = DOWNLOAD_DIR / f"{oid}-FINAL.pdf"
        if wants_qr:
            qr_value = f"endless://order/{r['order_code'] or oid}"
            add_qr_page(gray_pdf, qr_value, final_pdf)
        else:
            shutil.copyfile(gray_pdf, final_pdf)

        add_file(oid, 'processed_pdf', final_pdf, final_name=final_pdf.name)
        conn = db()
        conn.execute("UPDATE orders SET status=? WHERE id=?", ('processed', oid))
        conn.commit(); conn.close()
        ui.notify('PDF procesado y disponible en Descargas', color='positive')
        ui.run_javascript('window.location.reload()')

    ui.separator()
    with ui.row().classes('items-center'):
        ui.button('Procesar PDF', on_click=run_pipeline, color='primary', disabled=(not ok))
        if not ok and msg:
            ui.label(f'? {msg}').classes('text-amber-700')

    # vï¿½nculos de archivos del pedido
    with ui.expansion('Archivos del pedido', icon='folder').classes('mt-2').props('expand-separator'):
        for f in files_for_order(oid):
            ui.link(f['filename'], serve_path(Path(f['path']), f['filename']), new_tab=True)

# ------------------ Rutas ------------------
@ui.page('/')

def parse_orders(temp_path: Path):
    ext = temp_path.suffix.lower()
    try:
        if ext == ".csv":
            try:
                df = pd.read_csv(temp_path, encoding="utf-8-sig")
            except Exception:
                df = pd.read_csv(temp_path, encoding="latin1")
        else:
            df = pd.read_excel(temp_path)
    except Exception as e:
        ui.notify(f"Error leyendo archivo: {e}", color="negative")
        return 0
    n = 0
    for row in df.fillna("").to_dict("records"):
        try:
            upsert_order(row)
            n += 1
        except Exception as e:
            ui.notify(f"Fila con error: {e}", color="warning", timeout=6000)
    return n

    async def on_upload(e):
        # NiceGUI da .name y .content (file-like)
        up = e
        suffix = Path(up.name).suffix.lower()
        if suffix not in (".csv", ".xlsx", ".xls"):
            ui.notify("Solo se aceptan .csv, .xlsx, .xls", color="warning")
            return
        tmp = DATA_DIR / f"upload-{uuid.uuid4()}{suffix}"
        with open(tmp, "wb") as f:
            f.write(up.content.read())
        added = parse_orders(tmp)
        ui.notify(f"Importados: {added}", color="positive")
        ui.run_javascript('window.location.hash = "#pedidos"; window.location.reload()')

    ui.upload(label="Selecciona CSV/Excel", on_upload=on_upload) \
      .props("accept=.csv,.xlsx,.xls") \
      .classes("w-full")
def import_block():
    """Bloque UI para importar pedidos desde CSV/Excel sin endpoints FastAPI."""
    import tempfile
    from nicegui import events
    from pathlib import Path

    status = ui.label('Selecciona un CSV o Excel').classes('text-secondary')

    def on_upload(e: events.UploadEventArguments):
        try:
            if not e or not getattr(e, "name", None):
                ui.notify("No se recibió archivo", color="warning")
                return
            suffix = Path(e.name).suffix or ".csv"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(e.content.read())
                temp_path = Path(tmp.name)

            count = parse_orders(temp_path)
            status.set_text(f"Importadas {count} filas")
            ui.notify(f"Importadas {count} filas", color="positive")

        except Exception as ex:
            ui.notify(f"Error importando: {ex}", color="negative")

        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass

    ui.upload(
        label="Sube CSV o Excel",
        auto_upload=True,
        on_upload=on_upload
    ).props('accept=".csv,.xlsx,.xls"').classes("w-full")`r`n`r`n\ndef home():
    header()
    with ui.column().classes('max-w-5xl mx-auto'):
        import_block()
        ui.separator()
        ui.element('a').props('id=pedidos')
        page_list_orders()

@ui.page('/order/{oid}')
def order_detail(oid: str):
    header()
    with ui.column().classes('max-w-5xl mx-auto'):
        order_page(oid)

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    ui.run(reload=False, host='0.0.0.0', port=8090)

if __name__ == '__main__':
    main()

def fetch_orders():
    import sqlite3
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        'SELECT id, created_at, order_code, customer, email, cover, size, pages, wants_qr, wants_voice, tags FROM orders ORDER BY created_at DESC'
    )]
    con.close()
    return rows



def classes(s: str):
    el = ui.get_last_element()
    el.classes(s)
    return el

# === PATCHED order table ===
def to_row(r):
    return {
        'id': r.get('id'),
        'created': str(r.get('created_at','')).split('T')[0] if r.get('created_at') else '',
        'order': r.get('order_code', ''),
        'cliente': r.get('customer_name', ''),
        'email': r.get('email', ''),
        'cover': r.get('cover_type', ''),
        'size': r.get('size', ''),
        'pages': r.get('pages', ''),
        'qr': 'Sí' if r.get('wants_qr') else 'No',
        'voz': 'Sí' if r.get('wants_voice') else 'No',
        'estado': r.get('status', ''),
    }
def page_list_orders():
    import sqlite3
    from pathlib import Path

    def _db_path():
        try:
            return str(DB_PATH)
        except NameError:
            try:
                base = DATA_DIR
            except NameError:
                base = Path(__file__).parent / 'data'
                base.mkdir(parents=True, exist_ok=True)
            return str(base / 'app.db')

    def _fetch_orders(limit: int = 1000):
        conn = sqlite3.connect(_db_path())
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        base_cols = "id, created_at, order_code, customer_name, email, cover_type, size, pages, wants_qr, wants_voice"
        try:
            q = f"SELECT {base_cols}, COALESCE(status,'') AS status FROM orders ORDER BY created_at DESC LIMIT ?"
            rows = cur.execute(q, (limit,)).fetchall()
        except sqlite3.OperationalError:
            q = f"SELECT {base_cols} FROM orders ORDER BY created_at DESC LIMIT ?"
            rows = cur.execute(q, (limit,)).fetchall()
        out = [dict(r) for r in rows]
        conn.close()
        return out

    rows = _fetch_orders()
    if not rows:
        ui.label('Sin pedidos aún')
        return

    def to_row(r):
        return {
            'id': r.get('id'),
            'created': str(r.get('created_at','')).split('T')[0],
            'order': r.get('order_code',''),
            'cliente': r.get('customer_name',''),
            'email': r.get('email',''),
            'cover': r.get('cover_type',''),
            'size': r.get('size',''),
            'pages': r.get('pages',''),
            'qr': 'Sí' if r.get('wants_qr') else 'No',
            'voz': 'Sí' if r.get('wants_voice') else 'No',
            'estado': r.get('status',''),
        }

    ui.label('Pedidos').classes('text-xl font-bold mb-2')

    friendly_rows = [to_row(r) for r in rows]
    cols = [{'name': k, 'label': k.replace('_',' ').title(), 'field': k, 'sortable': True} for k in friendly_rows[0].keys()]
    t = ui.table(columns=cols, rows=friendly_rows, row_key='id').classes('w-full')

def on_row_click(e):
    # e.args puede venir como dict, lista, tupla o incluso None
    rid = None
    row = None
    a = getattr(e, 'args', None)

    if isinstance(a, dict):
        row = a.get('row') or a.get('rows') or a
    elif isinstance(a, (list, tuple)):
        for item in a:
            if isinstance(item, dict):
                cand = item.get('row', item)
                if isinstance(cand, dict):
                    row = cand
                    if any(k in row for k in ('id', 'key', 'pk')):
                        break

    if isinstance(row, dict):
        rid = row.get('id') or row.get('key') or row.get('pk')

    if rid:
        ui.open(f"/order/{rid}")
    else:
        ui.notify('No pude leer el id de la fila', color='warning')

    def parse_orders(temp_path: Path):
        ext = temp_path.suffix.lower()
        try:
            if ext == '.csv':
                try:
                    df = pd.read_csv(temp_path, encoding='utf-8-sig')
                except Exception:
                    df = pd.read_csv(temp_path, encoding='latin1')
            else:
                df = pd.read_excel(temp_path)
        except Exception as e:
            ui.notify(f'Error leyendo archivo: {e}', color='negative')
            return 0
        n = 0
        for row in df.fillna('').to_dict('records'):
            try:
                upsert_order(row)
                n += 1
            except Exception as e:
                ui.notify(f'Fila con error: {e}', color='warning', timeout=6000)
        return n

    async def on_upload(e):
        up = e  # NiceGUI entrega .name y .content
        suffix = Path(up.name).suffix.lower()
        if suffix not in ('.csv', '.xlsx', '.xls'):
            ui.notify('Solo se aceptan .csv, .xlsx, .xls', color='warning')
            return
        tmp = DATA_DIR / f"upload-{uuid.uuid4()}{suffix}"
        with open(tmp, 'wb') as f:
            f.write(up.content.read())
        added = parse_orders(tmp)
        ui.notify(f'Importados: {added}', color='positive')
        ui.run_javascript('window.location.hash = "#pedidos"; window.location.reload()')

    ui.upload(label='Selecciona CSV/Excel', on_upload=on_upload) \
      .props('accept=.csv,.xlsx,.xls') \
      .classes('w-full')
    def parse_orders(temp_path: Path) -> int:
        ext = temp_path.suffix.lower()
        try:
            if ext == '.csv':
                try:
                    df = pd.read_csv(temp_path, encoding='utf-8-sig')
                except Exception:
                    df = pd.read_csv(temp_path, encoding='latin1')
            else:
                df = pd.read_excel(temp_path)
        except Exception as e:
            ui.notify(f'Error leyendo archivo: {e}', color='negative')
            return 0

        upsert = globals().get('upsert_order')
        if upsert is None:
            ui.notify('No encuentro la función upsert_order()', color='negative')
            return 0

        n = 0
        for row in df.fillna('').to_dict('records'):
            try:
                upsert(row)
                n += 1
            except Exception as e:
                ui.notify(f'Fila con error: {e}', color='warning', timeout=6000)
        return n

    async def on_upload(e):
        up = e  # NiceGUI entrega .name y .content
        name = getattr(up, 'name', None)
        content = getattr(up, 'content', None)
        if not name or content is None:
            ui.notify('Evento de subida inválido', color='negative')
            return

        suffix = Path(name).suffix.lower()
        if suffix not in ('.csv', '.xlsx', '.xls'):
            ui.notify('Solo se aceptan .csv, .xlsx, .xls', color='warning')
            return

        tmp = base_dir / f"upload-{uuid.uuid4()}{suffix}"
        try:
            with open(tmp, 'wb') as f:
                f.write(content.read())
        except Exception as e:
            ui.notify(f'No pude guardar el archivo: {e}', color='negative')
            return

        added = parse_orders(tmp)
        ui.notify(f'Importados: {added}', color='positive')
        try:
            ui.run_javascript('window.location.hash = "#pedidos"; window.location.reload()')
        except Exception:
            pass

    ui.upload(label='Selecciona CSV/Excel', on_upload=on_upload).props('accept=.csv,.xlsx,.xls').classes('w-full')















