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
    """Ask for the Gemini API key if not already configured."""
    global api_button
    if main.GEMINI_API_KEY and main.GEMINI_API_KEY != 'tu_gemini':
        if api_button:
            api_button.destroy()
            api_button = None
        return
    key = simpledialog.askstring('Gemini API Key', 'Introduce tu clave de Gemini:', show='*')
    if key:
        os.environ['GEMINI_API_KEY'] = key
        main.GEMINI_API_KEY = key
        set_key(str(main.BASE_DIR / '.env'), 'GEMINI_API_KEY', key)
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
    missing = False
    for row in ORDERS:
        bbox = tree.bbox(row['id'], column='action')
        if not bbox:
            missing = True
            continue
        x, y, w, h = bbox
        premium = (
            row.get('cover', '').lower() == 'premium hardcover'
            and len(row.get('prompts', [])) > 1
        )
        buttons = ROW_BUTTONS.get(row['id'])
        if not buttons:
            buttons = []
            if premium:
                half = w // 2
                btn1 = Button(
                    tree,
                    text='Generar Libro',
                    command=lambda rid=row['id']: generate_order(rid),
                )
                btn2 = Button(
                    tree,
                    text='Copiar Prompt 2',
                    command=lambda rid=row['id']: copy_prompt2(rid),
                )
                buttons = [btn1, btn2]
            else:
                btn1 = Button(
                    tree,
                    text='Generar Libro',
                    command=lambda rid=row['id']: generate_order(rid),
                )
                buttons = [btn1]
            ROW_BUTTONS[row['id']] = buttons
        if premium and len(buttons) == 2:
            half = w // 2
            buttons[0].place(x=x, y=y, width=half, height=h)
            buttons[1].place(x=x + half, y=y, width=w - half, height=h)
        else:
            buttons[0].place(x=x, y=y, width=w, height=h)
    if missing:
        root.after(10, _place_buttons)


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
        webbrowser.open('https://gemini.google.com/gem/storybook', new=2)
        row['status'] = 'Prompt 2 copiado'
        refresh_table()
        messagebox.showinfo('Listo', 'Prompt 2 copiado al portapapeles')


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
tree.bind('<Configure>', lambda e: root.after(0, _place_buttons))

# Buttons
btns = Frame(root)
btns.pack(pady=5)
if not (main.GEMINI_API_KEY and main.GEMINI_API_KEY != 'tu_gemini'):
    api_button = Button(btns, text='Configurar API Key', command=prompt_api_key)
    api_button.pack(side='left', padx=5)
    prompt_api_key()
Button(btns, text='Cargar pedidos de prueba', command=load_samples).pack(side='left', padx=5)

root.mainloop()
