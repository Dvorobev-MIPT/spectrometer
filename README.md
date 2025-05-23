# Spectrometer

## Описание

**Spectrometer** — приложение для работы с камерой во время анализа спектров на базе Raspberry Pi.  
Позволяет получать изображение с камеры, настраивать параметры съёмки (яркость, контраст, экспозиция и др.), визуализировать и сохранять спектральные данные.  

Интерфейс реализован на PyQt5 и оптимизирован для работы с камерой Raspberry Pi (поддержка picamera2 и libcamera).  
Spectrometer подходит для учебных, лабораторных и исследовательских задач, связанных с анализом света и спектров.

Программа также позволяет точно перемещать линзы и камеру по оптической скамье с шагом 1 мм и погрешностью не более 5%, что удобно для экспериментов и юстировки оптической системы.

---

## Запуск

### Вариант 1. Сборка исполняемого файла

1. Перейдите в папку `./spectrometer/spectrometer_app/` и выполните установку:
   ```bash
   sudo pip install .
   ```
   или, если не работает:
   ```bash
   sudo python3 setup.py install
   ```
2. Перейдите в папку `./programm/spectrometer/`, сделайте скрипт исполняемым и соберите приложение:
   ```bash
   chmod +x build.sh
   ./build.sh
   ```
3. Готовый исполняемый файл появится в папке `./programm/spectrometer/`. Для запуска используйте файл `spectrometer`.

### Вариант 2. Запуск через main.py

1. Перейдите в папку `./spectrometer/spectrometer_app/` и выполните установку:
   ```bash
   sudo pip install .
   ```
   или:
   ```bash
   sudo python3 setup.py install
   ```
2. Запустите файл `main.py` любым удобным способом.

---

## Архитектура программы

Программа разделена на три основных модуля:

- **core**  
  Отвечает за взаимодействие с камерой через интерфейсы `picamera2` (вывод изображения) и `libcamera2` (настройка камеры). Также содержит интерфейсы управления перемещением оптических элементов.

- **ai**  
  Реализует пользовательский интерфейс (UI) программы, включая все элементы управления и визуализацию данных.

- **utils**  
  Содержит вспомогательные утилиты и функции для обработки данных, работы с файлами и другие служебные компоненты.

Описание компонентов каждого модуля представлено в следующей структуре:

![alt text](https://github.com/Dvorobev-MIPT/spectrometer/blob/main/images/spectrometer_structure.png)

---

## Возможные проблемы и их решения

### Нет изображения с камеры

Проверьте подключение камеры к Raspberry Pi и перезапустите устройство.
