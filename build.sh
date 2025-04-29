#!/bin/bash

# Путь к главному файлу приложения
MAIN_FILE="main.py"

# Имя итогового исполняемого файла
APP_NAME="spectrometer"

# Путь к иконке (должна быть .ico для Windows или .icns для macOS)
ICON_FILE="./spectrometer_app/resources/icon.ico"

# Папка для итоговой сборки
OUT_DIR="programm"

# Опция ускорения старта (распаковка во временную папку рядом с exe)
RUNTIME_TMPDIR="--runtime-tmpdir=."

# Проверка наличия PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "Ошибка: PyInstaller не установлен. Установите его командой: pip install pyinstaller"
    exit 1
fi

# Проверка наличия главного файла
if [ ! -f "$MAIN_FILE" ]; then
    echo "Ошибка: Главный файл $MAIN_FILE не найден!"
    exit 1
fi

# Проверка наличия иконки
if [ ! -f "$ICON_FILE" ]; then
    echo "Внимание: Файл иконки $ICON_FILE не найден. Сборка будет без иконки."
    ICON_ARG=""
else
    ICON_ARG="--icon=$ICON_FILE"
fi

# Проверка наличия UPX
if command -v upx &> /dev/null; then
    echo "UPX найден. Будет использовано сжатие бинарников."
    UPX_ARG=""
else
    echo "UPX не найден. Сборка будет без дополнительного сжатия."
    UPX_ARG="--noupx"
fi

# Очистка предыдущих сборок
rm -rf build "$OUT_DIR" *.spec

# Сборка с помощью PyInstaller с оптимизациями и выводом в OUT_DIR
pyinstaller --name "$APP_NAME" --onefile --windowed $ICON_ARG --strip --clean $UPX_ARG \
    $EXCLUDE_MODULES $RUNTIME_TMPDIR --distpath "$OUT_DIR" "$MAIN_FILE"

# Определение расширения исполняемого файла
EXT=""
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*|Windows_NT) EXT=".exe" ;;
esac

if [ -f "./$OUT_DIR/$APP_NAME$EXT" ]; then
    echo "Сборка завершена. Исполняемый файл находится в ./$OUT_DIR/$APP_NAME$EXT"
else
    echo "Ошибка: Исполняемый файл не был создан. Проверьте вывод PyInstaller выше."
    exit 1
fi
