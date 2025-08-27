
# Endless Chapters Studio

App local con interfaz para:
- Importar pedidos desde Excel/CSV
- Generar prompts (3 variantes) por pedido
- Subir texto (JSON o TXT) y audio (opcional)
- Producir PDF listo para imprenta (portada color con logo, interior en grises, QR a audio)
- Clonar voz a partir de un archivo de audio y generar locuciones del texto
- Previsualizar y abrir los archivos generados directamente desde la interfaz

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
- order_id, title, email, tags, notes, cover (hardcover/paperback), size, wants_voice, pages, voice_sample
(No todas son obligatorias; la app usa valores por defecto si faltan)

### Órdenes de prueba

Ejecuta `python generate_sample_orders.py` para crear `sample_orders.csv` con ejemplos que cubren combinaciones de etiquetas `voz` y `qr`, distintos tamaños y tipos de cubierta. Importa este archivo desde la interfaz para verificar que todo funcione correctamente.

## Empaquetar en .EXE (Windows)
```powershell
pip install pyinstaller
pyinstaller --name "EndlessChaptersStudio" --noconsole --add-data "assets;assets" main.py
```
El ejecutable quedará en `dist/EndlessChaptersStudio/`.
