param(
  [string]$Name = "EndlessChaptersStudio"
)
pip install pyinstaller
pyinstaller --name $Name --noconsole --add-data "assets;assets" main.py
Write-Host "EXE generado en dist\$Name\" -ForegroundColor Green
