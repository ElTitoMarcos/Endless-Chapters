from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Any
import uuid
import sqlite3
import zipfile
import tempfile
import io

import pandas as pd
from nicegui import ui, app
from fastapi import Request
from fastapi.responses import StreamingResponse, JSONResponse
from starlette.staticfiles import StaticFiles
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# ---------------------------------------------------------------------------
# Paths and logging
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / 'data'
DOWNLOAD_DIR = BASE_DIR / 'downloads'
DB_PATH = DATA_DIR / 'orders.db'
DATA_DIR.mkdir(exist_ok=True)
DOWNLOAD_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=DATA_DIR / 'app.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

# serve downloads
if not any(r.path == '/static/downloads' for r in app.routes if hasattr(r, 'path')):
    app.mount('/static/downloads', StaticFiles(directory=str(DOWNLOAD_DIR)), name='static-downloads')

# ---------------------------------------------------------------------------
# Models
@dataclass
class Item:
    sku: str
    qty: int
    language: Optional[str] = None
    title: Optional[str] = None
    personalization: Optional[str] = None
    pages: Optional[int] = None


@dataclass
class Order:
    id: str
    order_number: str
    created: date
    client: str
    email: str
    cover: str
    size: str
    pages: int
    language: Optional[str] = None
    tags: set[str] = field(default_factory=set)
    notes: Optional[str] = None
    status: str = 'pending'
    error_message: Optional[str] = None
    generated_at: Optional[datetime] = None
    output_dir: Optional[str] = None
    output_zip: Optional[str] = None


# ---------------------------------------------------------------------------
# Database helpers

def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def db_init() -> None:
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        '''CREATE TABLE IF NOT EXISTS orders(
               id TEXT PRIMARY KEY,
               order_number TEXT UNIQUE,
               created TEXT,
               client TEXT,
               email TEXT,
               cover TEXT,
               size TEXT,
               pages INTEGER,
               language TEXT,
               tags TEXT,
               notes TEXT,
               status TEXT,
               error_message TEXT,
               generated_at TEXT,
               output_dir TEXT,
               output_zip TEXT
           );'''
    )
    cur.execute(
        '''CREATE TABLE IF NOT EXISTS order_items(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               order_id TEXT,
               sku TEXT,
               qty INTEGER,
               language TEXT,
               title TEXT,
               personalization TEXT,
               pages INTEGER
           );'''
    )
    conn.commit()
    conn.close()


def db_upsert_order(order: Order, items: list[Item]) -> str:
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('SELECT id, status FROM orders WHERE order_number=?', (order.order_number,))
    row = cur.fetchone()
    if row:
        order.id = row['id']
        prev_status = row['status']
        status = 'done' if prev_status == 'done' else 'pending'
        cur.execute('''UPDATE orders SET created=?, client=?, email=?, cover=?, size=?,
                       pages=?, language=?, tags=?, notes=?, status=? WHERE id=?''',
                    (order.created.isoformat(), order.client, order.email, order.cover,
                     order.size, order.pages, order.language,
                     ','.join(sorted(order.tags)), order.notes, status, order.id))
        cur.execute('DELETE FROM order_items WHERE order_id=?', (order.id,))
    else:
        order.id = str(uuid.uuid4())
        cur.execute('''INSERT INTO orders(id, order_number, created, client, email, cover, size, pages,
                       language, tags, notes, status)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (order.id, order.order_number, order.created.isoformat(), order.client,
                     order.email, order.cover, order.size, order.pages, order.language,
                     ','.join(sorted(order.tags)), order.notes, order.status))
    for it in items:
        cur.execute('''INSERT INTO order_items(order_id, sku, qty, language, title, personalization, pages)
                       VALUES(?,?,?,?,?,?,?)''',
                    (order.id, it.sku, it.qty, it.language, it.title, it.personalization, it.pages))
    conn.commit()
    conn.close()
    return order.id


def db_list_orders() -> list[sqlite3.Row]:
    conn = db_connect()
    rows = conn.execute('SELECT * FROM orders ORDER BY datetime(created) DESC').fetchall()
    conn.close()
    return rows


def db_get_order(oid: str) -> tuple[Order, list[Item]]:
    conn = db_connect()
    order_row = conn.execute('SELECT * FROM orders WHERE id=?', (oid,)).fetchone()
    if not order_row:
        raise KeyError('order not found')
    item_rows = conn.execute('SELECT * FROM order_items WHERE order_id=?', (oid,)).fetchall()
    conn.close()
    order = Order(
        id=order_row['id'],
        order_number=order_row['order_number'],
        created=datetime.fromisoformat(order_row['created']).date(),
        client=order_row['client'],
        email=order_row['email'],
        cover=order_row['cover'],
        size=order_row['size'],
        pages=order_row['pages'],
        language=order_row['language'],
        tags=set(filter(None, (order_row['tags'] or '').split(','))),
        notes=order_row['notes'],
        status=order_row['status'],
        error_message=order_row['error_message'],
        generated_at=datetime.fromisoformat(order_row['generated_at']) if order_row['generated_at'] else None,
        output_dir=order_row['output_dir'],
        output_zip=order_row['output_zip']
    )
    items = [Item(sku=r['sku'], qty=r['qty'], language=r['language'],
                  title=r['title'], personalization=r['personalization'],
                  pages=r['pages']) for r in item_rows]
    return order, items


def db_update_status(oid: str, status: str, error_message: str | None = None,
                     output_dir: str | None = None, output_zip: str | None = None) -> None:
    conn = db_connect()
    params: list[Any] = [status, error_message, output_dir, output_zip]
    sql = 'UPDATE orders SET status=?, error_message=?, output_dir=?, output_zip=?'
    if status == 'done':
        sql += ', generated_at=?'
        params.append(datetime.now().isoformat())
    sql += ' WHERE id=?'
    params.append(oid)
    conn.execute(sql, params)
    conn.commit()
    conn.close()

# ---------------------------------------------------------------------------
# Parsing helpers


def parse_items(raw: str) -> list[Item]:
    items: list[Item] = []
    raw = raw.strip()
    if not raw:
        return items
    try:
        if raw.startswith('[') or raw.startswith('{'):
            data = json.loads(raw)
            for d in data:
                items.append(Item(
                    sku=str(d.get('sku')),
                    qty=int(d.get('qty', 1)),
                    language=d.get('language'),
                    title=d.get('title'),
                    personalization=d.get('personalization'),
                    pages=d.get('pages')
                ))
            return items
    except Exception:
        pass
    # DSL SKU:QTY@lang#title#personalization | ...
    parts = [p.strip() for p in raw.split('|') if p.strip()]
    for part in parts:
        sku_qty, *after_at = part.split('@', 1)
        if ':' in sku_qty:
            sku_part, qty_str = sku_qty.split(':', 1)
            qty = int(qty_str or 1)
        else:
            sku_part = sku_qty
            qty = 1
        lang = title = pers = None
        if after_at:
            lang_title = after_at[0].split('#')
            if len(lang_title) > 0:
                lang = lang_title[0] or None
            if len(lang_title) > 1:
                title = lang_title[1] or None
            if len(lang_title) > 2:
                pers = lang_title[2] or None
        items.append(Item(sku=sku_part, qty=qty, language=lang, title=title,
                          personalization=pers))
    return items


COLUMN_ALIASES = {
    'order_number': ['order', 'order_number'],
    'client': ['client', 'cliente', 'name'],
    'email': ['email'],
    'items': ['items'],
    'cover': ['cover'],
    'size': ['size'],
    'pages': ['pages'],
    'language': ['language', 'lang'],
    'tags': ['tags'],
    'notes': ['notes'],
    'created': ['created']
}


def _col(row: dict, key: str) -> Any:
    for alt in COLUMN_ALIASES[key]:
        if alt in row and pd.notna(row[alt]):
            return row[alt]
    return None


def parse_orders(temp_path: Path) -> list[str]:
    if temp_path.suffix.lower() in {'.xlsx', '.xls'}:
        df = pd.read_excel(temp_path)
    else:
        try:
            df = pd.read_csv(temp_path, encoding='utf-8-sig')
        except Exception:
            df = pd.read_csv(temp_path, encoding='latin1')
    ids: list[str] = []
    for _, row in df.iterrows():
        data = row.to_dict()
        items = parse_items(str(_col(data, 'items') or ''))
        pages = _col(data, 'pages')
        if pages is None:
            pages = sum((it.pages or 0) * it.qty for it in items)
        try:
            pages = int(pages)
        except Exception:
            pages = 0
        tags = set()
        tags_raw = str(_col(data, 'tags') or '')
        if tags_raw:
            tags = {t.strip().lower() for t in tags_raw.split(',') if t.strip()}
        created_val = _col(data, 'created')
        if created_val:
            try:
                created = datetime.fromisoformat(str(created_val)).date()
            except Exception:
                created = date.today()
        else:
            created = date.today()
        order = Order(
            id='',
            order_number=str(_col(data, 'order_number') or ''),
            created=created,
            client=str(_col(data, 'client') or ''),
            email=str(_col(data, 'email') or ''),
            cover=str(_col(data, 'cover') or ''),
            size=str(_col(data, 'size') or ''),
            pages=pages,
            language=_col(data, 'language'),
            tags=tags,
            notes=str(_col(data, 'notes') or '') or None
        )
        oid = db_upsert_order(order, items)
        ids.append(oid)
    return ids

# ---------------------------------------------------------------------------
# PDF generation
SIZE_MAP = {
    '5x5': (5*inch, 5*inch),
    '5x8': (5*inch, 8*inch),
    '6x9': (6*inch, 9*inch),
    '7x10': (7*inch, 10*inch),
    '8x8': (8*inch, 8*inch),
}


def generate_order_pdf(order_uuid: str) -> Path:
    order, items = db_get_order(order_uuid)
    folder = DOWNLOAD_DIR / f"{order.order_number}_{order_uuid[:8]}"
    folder.mkdir(parents=True, exist_ok=True)
    pagesize = SIZE_MAP.get(order.size.lower(), (6*inch, 9*inch))
    # interior
    interior_path = folder / 'interior.pdf'
    c = canvas.Canvas(str(interior_path), pagesize=pagesize)
    for it in items:
        for i in range(it.qty):
            text = c.beginText(40, pagesize[1]-40)
            text.textLine(f'SKU: {it.sku}')
            text.textLine(f'Cantidad: {it.qty}')
            if it.title:
                text.textLine(f'Título: {it.title}')
            if it.personalization:
                text.textLine(f'Perso: {it.personalization}')
            c.drawText(text)
            c.showPage()
    c.save()
    # cover
    cover_path = folder / 'cover.pdf'
    c = canvas.Canvas(str(cover_path), pagesize=pagesize)
    text = c.beginText(40, pagesize[1]-40)
    if items and items[0].title:
        text.textLine(items[0].title)
    text.textLine(order.client)
    text.textLine(f'Pedido {order.order_number}')
    text.textLine(order.created.isoformat())
    c.drawText(text)
    c.showPage()
    if 'qr' in order.tags:
        qr_img = qrcode.make(f"https://example.com/order/{order.order_number}")
        qr_path = folder / 'qr.png'
        qr_img.save(qr_path)
        c.drawImage(str(qr_path), pagesize[0]/2-72, pagesize[1]/2-72, 144, 144)
    c.save()
    # invoice
    if 'invoice' in order.tags:
        invoice_path = folder / 'invoice.pdf'
        c = canvas.Canvas(str(invoice_path), pagesize=pagesize)
        c.drawString(40, pagesize[1]-40, f'Factura de {order.client} - {order.order_number}')
        c.showPage()
        c.save()
    db_update_status(order_uuid, 'done', output_dir=str(folder.relative_to(DOWNLOAD_DIR)))
    return folder


def generate_many(order_ids: list[str]) -> Path:
    zip_name = f'lote_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
    zip_path = DOWNLOAD_DIR / zip_name
    paths = []
    for oid in order_ids:
        try:
            db_update_status(oid, 'generating')
            folder = generate_order_pdf(oid)
            paths.append(folder)
        except Exception as e:
            logger.exception('error generating %s', oid)
            db_update_status(oid, 'error', error_message=str(e))
    with zipfile.ZipFile(zip_path, 'w') as z:
        for p in paths:
            for f in p.rglob('*'):
                z.write(f, arcname=p.name + '/' + f.name)
    for oid in order_ids:
        order, _ = db_get_order(oid)
        if order.status == 'done':
            db_update_status(oid, 'done', output_zip=str(zip_path.relative_to(DOWNLOAD_DIR)))
    return zip_path

# ---------------------------------------------------------------------------
# UI components

def import_block() -> None:
    async def handle_upload(e: ui.UploadEventArguments) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=e.name) as tmp:
            tmp.write(e.content.read())
            tmp_path = Path(tmp.name)
        ids = parse_orders(tmp_path)
        ui.notify(f'Se importaron {len(ids)} pedidos')
    with ui.card().classes('p-4'):
        ui.label('Importar pedidos (CSV/Excel)')
        ui.upload(on_upload=handle_upload, multiple=False, auto_upload=True)


selected_orders: list[str] = []


def show_order_dialog(order_id: str) -> None:
    order, items = db_get_order(order_id)
    with ui.dialog() as dialog, ui.card():
        ui.label(f'Pedido {order.order_number}').classes('text-lg')
        ui.label(f'Cliente: {order.client}')
        ui.label(f'Email: {order.email}')
        ui.label(f'Tags: {", ".join(sorted(order.tags))}')
        if order.notes:
            ui.label(f'Notas: {order.notes}')
        if order.status == 'error' and order.error_message:
            ui.label(f'Error: {order.error_message}').classes('text-red')
        with ui.table(columns=[
                {'name': 'sku', 'label': 'SKU', 'field': 'sku'},
                {'name': 'qty', 'label': 'Cant', 'field': 'qty'},
                {'name': 'title', 'label': 'Título', 'field': 'title'},
            ],
            rows=[{'sku': it.sku, 'qty': it.qty, 'title': it.title or ''} for it in items]):
            pass
        with ui.row():
            ui.button('Generar este pedido', on_click=lambda: generate_one(order_id, dialog))
            if order.output_dir:
                ui.button('Abrir carpeta de salida',
                          on_click=lambda: ui.open(f'/static/downloads/{order.output_dir}'))
            ui.button('Marcar como pendiente', on_click=lambda: (db_update_status(order_id,'pending'), ui.notify('Estado actualizado')))
            ui.button('Cerrar', on_click=dialog.close)
    dialog.open()


def generate_one(order_id: str, dialog: ui.dialog) -> None:
    try:
        db_update_status(order_id, 'generating')
        generate_order_pdf(order_id)
        ui.notify('Generado')
    except Exception as e:
        db_update_status(order_id, 'error', error_message=str(e))
        ui.notify('Error al generar', type='negative')
    dialog.close()


def page_list_orders() -> None:
    global selected_orders
    selected_orders = []
    rows = [dict(r) for r in db_list_orders()]
    columns = [
        {'name':'select','label':'','field':'id','sortable':False},
        {'name':'order_number','label':'Pedido','field':'order_number'},
        {'name':'client','label':'Cliente','field':'client'},
        {'name':'pages','label':'Páginas','field':'pages'},
        {'name':'status','label':'Status','field':'status'},
    ]
    def on_selection(e: dict) -> None:
        selected_orders[:] = e.get('selection', [])
    def on_row_click(e: dict) -> None:
        show_order_dialog(e['row']['id'])
    with ui.page('/'):  # home
        with ui.row().classes('items-center'):
            ui.button('Generar seleccionados', on_click=lambda: generate_selected())
            ui.button('Exportar CSV', on_click=lambda: ui.open('/api/export.csv'))
            ui.button('Refrescar', on_click=lambda: ui.open('/'))
        ui.table(columns=columns, rows=rows, row_key='id',
                 selection='multiple', on_select=on_selection,
                 on_row_click=on_row_click)
        import_block()


def generate_selected() -> None:
    if not selected_orders:
        ui.notify('No hay pedidos seleccionados')
        return
    try:
        generate_many(selected_orders)
        ui.notify('Pedidos generados')
    except Exception as e:
        ui.notify(f'Error: {e}', type='negative')


# descargas page

def page_downloads() -> None:
    files = sorted(DOWNLOAD_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    with ui.page('/descargas'):
        ui.label('Descargas').classes('text-lg')
        for f in files:
            with ui.row():
                ui.button(f.name, on_click=lambda f=f: ui.open(f'/static/downloads/{f.name}'))
                ui.label(datetime.fromtimestamp(f.stat().st_mtime).isoformat())
                ui.label(f'{f.stat().st_size} bytes')
                ui.button('Borrar', on_click=lambda f=f: (f.unlink(), ui.open('/descargas')))


# ---------------------------------------------------------------------------
# API


@app.get('/api/orders')
def api_orders(request: Request, status: str | None = None, q: str | None = None):
    rows = [dict(r) for r in db_list_orders()]
    if status:
        rows = [r for r in rows if r['status'] == status]
    if q:
        rows = [r for r in rows if q.lower() in r['order_number'].lower()]
    return JSONResponse(rows)


@app.post('/api/generate')
async def api_generate(data: dict):
    ids = data.get('ids', [])
    path = generate_many(ids)
    return {'zip_path': f'/static/downloads/{path.name}'}


@app.get('/api/export.csv')
def api_export_csv():
    rows = db_list_orders()
    def gen():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['order_number','client','email','cover','size','pages','language','tags','notes','status'])
        for r in rows:
            writer.writerow([r['order_number'], r['client'], r['email'], r['cover'], r['size'],
                             r['pages'], r['language'], r['tags'], r['notes'], r['status']])
        yield output.getvalue()
    return StreamingResponse(gen(), media_type='text/csv', headers={'Content-Disposition':'attachment; filename="orders.csv"'})


# ---------------------------------------------------------------------------
# Run

def home():
    page_list_orders()
    page_downloads()

if __name__ == '__main__':
    db_init()
    home()
    ui.run()
