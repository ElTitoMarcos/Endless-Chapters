
# Endless Chapters Studio

App local con interfaz para:
- Importar pedidos desde Excel/CSV
- Configurar y verificar la clave de OpenAI
- Generar prompts por pedido automáticamente usando GPT-4o
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
Al arrancar se solicitará tu clave de OpenAI y luego se abrirá una ventana con los pedidos de prueba.

> Nota: la clonación de voz con muestras requiere la librería opcional `TTS`, disponible solo para versiones de Python anteriores a 3.12. Si no está instalada, la aplicación usará `pyttsx3` con una voz genérica.

### Clave de API de OpenAI

La aplicación pedirá la clave de OpenAI si no está configurada. Puedes volver a cambiarla desde el botón "Configurar API Key". Esta clave se utiliza para generar los prompts de Gemini Storybook con el modelo GPT-4o y para las funciones de voz que requieran OpenAI. Tras introducirla se guarda en el archivo `.env`.

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

### Flujo de estados
Cada pedido avanza por los siguientes estados: "Prompt ready" → "Pending yo revise PDF" → "DONE". La interfaz muestra un botón de acción para continuar con el siguiente paso según corresponda.

## Empaquetar en .EXE (Windows)
```powershell
pip install pyinstaller
pyinstaller --name "EndlessChaptersStudio" --noconsole --add-data "assets;assets" main.py
```
El ejecutable quedará en `dist/EndlessChaptersStudio/`.
