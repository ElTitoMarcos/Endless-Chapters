from __future__ import annotations

import os
import threading
import webbrowser
from tkinter import Tk, Frame, Button, messagebox, simpledialog
from tkinter import ttk

import pyperclip

import main
from main import generate_prompts, synth_voice, generate_order_bundle, DOWNLOAD_DIR
from dotenv import set_key
from sample_orders import get_sample_orders

ORDERS: list[dict] = []


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
    if main.OPENAI_API_KEY and main.OPENAI_API_KEY != 'tu_openai':
        return
    key = simpledialog.askstring('OpenAI API Key', 'Introduce tu clave de OpenAI:', show='*')
    if key:
        os.environ['OPENAI_API_KEY'] = key
        main.OPENAI_API_KEY = key
        set_key(str(main.BASE_DIR / '.env'), 'OPENAI_API_KEY', key)

def refresh_table() -> None:
    tree.delete(*tree.get_children())
    for row in ORDERS:
        tree.insert('', 'end', iid=row['id'], values=(row['order'], row['client'], row.get('status', '')))


def generate_selected() -> None:
    sel = tree.selection()
    if not sel:
        messagebox.showwarning('Selección', 'Selecciona un pedido')
        return
    row = next(r for r in ORDERS if r['id'] == sel[0])

    def task() -> None:
        # copy first prompt and open Storybook
        if row.get('prompts'):
            pyperclip.copy(row['prompts'][0])
            webbrowser.open('https://gemini.google.com/gem/storybook', new=2)
        audio_dir = DOWNLOAD_DIR / f"order_{row['order']}_{row['id']}" / 'audio'
        synth_voice(row, audio_dir)
        work_dir, _ = generate_order_bundle(row, DOWNLOAD_DIR)
        row['status'] = 'Pending yo revise PDF'
        refresh_table()
        messagebox.showinfo('Listo', f"Libro generado en {work_dir}")

    threading.Thread(target=task, daemon=True).start()


root = Tk()
root.title('Endless Chapters')

# Table of orders
columns = ('order', 'client', 'status')
tree = ttk.Treeview(root, columns=columns, show='headings')
for col, title in zip(columns, ['Pedido', 'Cliente', 'Estado']):
    tree.heading(col, text=title)
    tree.column(col, width=150)
tree.pack(fill='both', expand=True)

# Buttons
btns = Frame(root)
btns.pack(pady=5)
Button(btns, text='Configurar API Key', command=prompt_api_key).pack(side='left', padx=5)
Button(btns, text='Cargar pedidos de prueba', command=load_samples).pack(side='left', padx=5)
Button(btns, text='Generar Libro', command=generate_selected).pack(side='left', padx=5)

# Prompt for key and load initial sample orders
prompt_api_key()
load_samples()
root.mainloop()
