
# Endless Chapters Studio

App local con interfaz para:
- Importar pedidos desde Excel/CSV
- Generar prompts (3 variantes) por pedido
- Subir texto (JSON o TXT) y audio (opcional)
- Producir PDF listo para imprenta (portada color con logo, interior en grises, QR a audio)

## Requisitos
- Python 3.10+
- Windows/Mac/Linux

## Instalación
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```
Abrirá el navegador en http://127.0.0.1:8080

## Columnas reconocidas en Excel/CSV
- order_id, title, email, tags, notes, cover (hardcover/paperback), size, wants_narr, pages
(No todas son obligatorias; la app usa valores por defecto si faltan)

## Empaquetar en .EXE (Windows)
```powershell
pip install pyinstaller
pyinstaller --name "EndlessChaptersStudio" --noconsole --add-data "assets;assets" main.py
```
El ejecutable quedará en `dist/EndlessChaptersStudio/`.
