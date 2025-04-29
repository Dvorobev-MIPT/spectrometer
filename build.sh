#!/bin/bash

# Путь к главному файлу приложения
MAIN_FILE="main.py"

# Имя итогового исполняемого файла
APP_NAME="spectrometer"

# Очистка предыдущих сборок
rm -rf build dist *.spec

# Сборка с помощью PyInstaller
pyinstaller --name "$APP_NAME" --onefile --windowed "$MAIN_FILE"

echo "Сборка завершена. Исполняемый файл находится в ./dist/$APP_NAME"