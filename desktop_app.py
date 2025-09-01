from __future__ import annotations

import threading
import webbrowser
from tkinter import Tk, Frame, Button, messagebox
from tkinter import ttk

import pyperclip
from main import generate_prompts, synth_voice, generate_order_bundle, DOWNLOAD_DIR
from sample_orders import get_sample_orders

ORDERS: list[dict] = []


def load_samples() -> None:
    """Load three sample orders and populate the table."""
    ORDERS.clear()
    samples = get_sample_orders()
    for s in samples:
        generate_prompts(s)
        ORDERS.append(s)
    refresh_table()


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
Button(btns, text='Cargar pedidos de prueba', command=load_samples).pack(side='left', padx=5)
Button(btns, text='Generar Libro', command=generate_selected).pack(side='left', padx=5)

# Load initial sample orders
load_samples()
root.mainloop()
