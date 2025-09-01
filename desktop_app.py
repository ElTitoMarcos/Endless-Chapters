from __future__ import annotations

import webbrowser
from tkinter import Tk, Frame, Button, messagebox, filedialog
from tkinter import ttk

import pyperclip

from pathlib import Path
import tempfile

from main import (
    prepare_notebook_text,
    books_for_cover,
    synth_voice,
    generate_order_bundle,
    DOWNLOAD_DIR,
    ASSETS_DIR,
)
from postprocess import postprocess_storybooks
from sample_orders import get_sample_orders

ORDERS: list[dict] = []
ROW_BUTTONS: dict[str, list[Button]] = {}

def load_samples() -> None:
    """Load three sample orders and populate the table."""
    ORDERS.clear()
    samples = get_sample_orders()
    for s in samples:
        try:
            prepare_notebook_text(s)
            ORDERS.append(s)
        except Exception as e:
            messagebox.showerror('Error', f'No se pudieron preparar los datos: {e}')
            break
    refresh_table()

def refresh_table() -> None:
    tree.delete(*tree.get_children())
    for btns in ROW_BUTTONS.values():
        for btn in btns:
            btn.destroy()
    ROW_BUTTONS.clear()
    for row in ORDERS:
        tree.insert(
            '',
            'end',
            iid=row['id'],
            values=(
                row['order'],
                row['client'],
                row.get('email', ''),
                row.get('cover', ''),
                row.get('personalized_characters', 0),
                row.get('narration', ''),
                row.get('revisions', 0),
                row.get('status', ''),
                '',
            ),
        )
    root.after(0, _place_buttons)


def _place_buttons() -> None:
    for row in ORDERS:
        bbox = tree.bbox(row['id'], column='action')
        if not bbox:
            root.after(10, _place_buttons)
            return
        x, y, w, h = bbox[0], bbox[1], bbox[2], bbox[3]
        buttons: list[Button] = []
        status = row.get('status', '')
        if status == 'Pending to NotebookLM':
            btn = Button(
                tree,
                text='NotebookLM',
                command=lambda rid=row['id']: open_notebooklm(rid),
            )
            btn.place(x=x, y=y, width=w, height=h)
            buttons.append(btn)
        elif status == 'Pending to Storybook':
            btn = Button(
                tree,
                text='Generar Storybook',
                command=lambda rid=row['id']: open_storybook(rid),
            )
            btn.place(x=x, y=y, width=w, height=h)
            buttons.append(btn)
        elif status == 'Pending storybook upload':
            btn = Button(
                tree,
                text='Subir Storybook',
                command=lambda rid=row['id']: upload_storybook(rid),
            )
            btn.place(x=x, y=y, width=w, height=h)
            buttons.append(btn)
        ROW_BUTTONS[row['id']] = buttons


def open_notebooklm(row_id: str) -> None:
    row = next(r for r in ORDERS if r['id'] == row_id)
    text = row.get('notebook_text', '')
    if text:
        pyperclip.copy(text)
    webbrowser.open('https://notebooklm.google.com/notebook', new=2)
    row['status'] = 'Pending to Storybook'
    refresh_table()
    messagebox.showinfo('Listo', 'Texto copiado para NotebookLM')


def open_storybook(row_id: str) -> None:
    row = next(r for r in ORDERS if r['id'] == row_id)
    webbrowser.open('https://gemini.google.com/gem/storybook', new=2)
    row['status'] = 'Pending storybook upload'
    refresh_table()
    messagebox.showinfo('Listo', 'Genera el Storybook y luego súbelo')


def upload_storybook(row_id: str) -> None:
    row = next(r for r in ORDERS if r['id'] == row_id)
    expected = books_for_cover(row.get('cover', ''))
    files = filedialog.askopenfilenames(filetypes=[('PDF', '*.pdf')])
    if not files:
        return
    if len(files) != expected:
        messagebox.showerror('Error', f'Se esperaban {expected} archivos')
        return
    try:
        temp_dir = Path(tempfile.mkdtemp())
        paths = [Path(f) for f in files]
        final_pdf = temp_dir / 'storybook.pdf'
        postprocess_storybooks(paths, final_pdf, ASSETS_DIR / 'logo nuevo png.png')
        audio_dir = DOWNLOAD_DIR / f"order_{row['order']}_{row['id']}" / 'audio'
        synth_voice(row, audio_dir)
        generate_order_bundle(row, DOWNLOAD_DIR, final_pdf)
        row['status'] = 'Pending yo revise PDF'
        messagebox.showinfo('Listo', 'Storybook procesado')
    except Exception as e:
        messagebox.showerror('Error', f'No se pudo procesar: {e}')
    refresh_table()


root = Tk()
root.title('Endless Chapters')

columns = (
    'order',
    'client',
    'email',
    'cover',
    'personalized_characters',
    'narration',
    'revisions',
    'status',
    'action',
)
tree = ttk.Treeview(root, columns=columns, show='headings')
headers = [
    'Pedido',
    'Cliente',
    'Email',
    'Cubierta',
    'Personajes',
    'Narración',
    'Revisiones',
    'Estado',
    '',
]
widths = [80, 120, 160, 120, 80, 120, 80, 120, 120]
for col, title, w in zip(columns, headers, widths):
    tree.heading(col, text=title)
    tree.column(col, width=w)
tree.pack(fill='both', expand=True)

# Buttons
btns = Frame(root)
btns.pack(pady=5)
Button(btns, text='Cargar pedidos de prueba', command=load_samples).pack(side='left', padx=5)

root.mainloop()

