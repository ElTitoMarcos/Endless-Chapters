from __future__ import annotations

import os
import webbrowser
from tkinter import Tk, Frame, Button, messagebox, simpledialog
from tkinter import ttk

import pyperclip

import main
from main import generate_prompts
from dotenv import set_key
from sample_orders import get_sample_orders

ORDERS: list[dict] = []
ROW_BUTTONS: dict[str, list[Button]] = {}
api_button: Button | None = None

def load_samples() -> None:
    """Load three sample orders and populate the table."""
    ORDERS.clear()
    samples = get_sample_orders()
    for s in samples:
        try:
            generate_prompts(s)
            ORDERS.append(s)
        except Exception as e:
            messagebox.showerror('Error', f'No se pudieron generar prompts: {e}')
            break
    refresh_table()


def prompt_api_key() -> None:
    """Ask the user for the OpenAI API key if not already configured."""
    global api_button
    if main.OPENAI_API_KEY and main.OPENAI_API_KEY != 'tu_openai':
        if api_button:
            api_button.destroy()
            api_button = None
        return
    key = simpledialog.askstring('OpenAI API Key', 'Introduce tu clave de OpenAI:', show='*')
    if key:
        os.environ['OPENAI_API_KEY'] = key
        main.OPENAI_API_KEY = key
        set_key(str(main.BASE_DIR / '.env'), 'OPENAI_API_KEY', key)
        if api_button:
            api_button.destroy()
            api_button = None

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
        premium = row.get('cover', '').lower() == 'premium hardcover'
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
                text='Guardar Prompts',
                command=lambda rid=row['id']: save_prompts(rid),
            )
            btn.place(x=x, y=y, width=w, height=h)
            buttons.append(btn)
        elif status == 'ready to generate Book':
            if premium and len(row.get('prompts', [])) > 1:
                half = w // 2
                btn1 = Button(
                    tree,
                    text='Generar Libro',
                    command=lambda rid=row['id']: generate_order(rid),
                )
                btn1.place(x=x, y=y, width=half, height=h)
                btn2 = Button(
                    tree,
                    text='Copiar Prompt 2',
                    command=lambda rid=row['id']: copy_prompt2(rid),
                )
                btn2.place(x=x + half, y=y, width=w - half, height=h)
                buttons.extend([btn1, btn2])
            else:
                btn1 = Button(
                    tree,
                    text='Generar Libro',
                    command=lambda rid=row['id']: generate_order(rid),
                )
                btn1.place(x=x, y=y, width=w, height=h)
                buttons.append(btn1)
        ROW_BUTTONS[row['id']] = buttons


def generate_order(row_id: str) -> None:
    row = next(r for r in ORDERS if r['id'] == row_id)
    if row.get('prompts'):
        pyperclip.copy(row['prompts'][0])
        webbrowser.open('https://gemini.google.com/gem/storybook', new=2)
        row['status'] = 'Prompt 1 copiado'
        refresh_table()
        messagebox.showinfo('Listo', 'Prompt 1 copiado al portapapeles')

def copy_prompt2(row_id: str) -> None:
    row = next(r for r in ORDERS if r['id'] == row_id)
    if len(row.get('prompts', [])) > 1:
        pyperclip.copy(row['prompts'][1])
        messagebox.showinfo('Listo', 'Prompt 2 copiado al portapapeles')


def open_notebooklm(row_id: str) -> None:
    row = next(r for r in ORDERS if r['id'] == row_id)
    text = row.get('notebook_text', '')
    if text:
        pyperclip.copy(text)
    webbrowser.open('https://notebooklm.google.com/notebook', new=2)
    row['status'] = 'Pending to Storybook'
    refresh_table()
    messagebox.showinfo('Listo', 'Texto copiado para NotebookLM')


def save_prompts(row_id: str) -> None:
    row = next(r for r in ORDERS if r['id'] == row_id)
    text = pyperclip.paste()
    prompts = [p.strip() for p in text.split('\n---\n') if p.strip()]
    row['prompts'] = prompts
    row['status'] = 'ready to generate Book'
    refresh_table()
    messagebox.showinfo('Listo', 'Prompts guardados')

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
if not (main.OPENAI_API_KEY and main.OPENAI_API_KEY != 'tu_openai'):
    api_button = Button(btns, text='Configurar API Key', command=prompt_api_key)
    api_button.pack(side='left', padx=5)
    prompt_api_key()
Button(btns, text='Cargar pedidos de prueba', command=load_samples).pack(side='left', padx=5)

root.mainloop()
