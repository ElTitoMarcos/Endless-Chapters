
# Endless Chapters Studio

App local con interfaz para:
- Importar pedidos desde Excel/CSV
- Copiar texto para NotebookLM que inicia con "Genera una historia a partir de la siguiente información" y agrega notas de personajes personalizados y sus fotos
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
python desktop_app.py
```
Al arrancar se abrirá una ventana vacía; pulsa "Cargar pedidos de prueba" para ver ejemplos.

> Nota: la clonación de voz con muestras requiere la librería opcional `TTS`, disponible solo para versiones de Python anteriores a 3.12. Si no está instalada, la aplicación usará `pyttsx3` con una voz genérica.

## Columnas reconocidas en Excel/CSV
- order, title, email, tags, notes, cover (Premium Hardcover/Standard Hardcover), personalized_characters, narration, revisions, voice_sample
(No todas son obligatorias; la app usa valores por defecto si faltan)

### Opciones de personalización
- **Cubierta:** Premium Hardcover, Standard Hardcover
- **Personajes personalizados:** 0-3
- **Narración:** Narrated by your loved one, None
- **Revisiones:** 0-3

### Órdenes de prueba

Ejecuta `python generate_sample_orders.py` para crear `sample_orders.csv` con ejemplos que cubren combinaciones de etiquetas `voz` y `qr` y distintos tipos de cubierta. Importa este archivo desde la interfaz para verificar que todo funcione correctamente.

El botón **Generar Storybook** abre la página de Gemini Storybook sin descargar archivos. Aparece después de copiar en NotebookLM el resumen generado allí.

### Flujo de estados
Cada pedido avanza por los siguientes estados: "Pending to NotebookLM" → "Pending to Storybook" → "Pending yo revise PDF" → "DONE". La interfaz muestra un botón de acción para continuar con el siguiente paso según corresponda.

## Empaquetar en .EXE (Windows)
```powershell
pip install pyinstaller
pyinstaller --name "EndlessChaptersStudio" --noconsole --add-data "assets;assets" main.py
```
El ejecutable quedará en `dist/EndlessChaptersStudio/`.
