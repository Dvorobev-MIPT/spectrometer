# spectrometer_app/ui/dialogs.py

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QGroupBox, QMessageBox, QComboBox, QSlider)
from PyQt5.QtCore import Qt

try:
    from spectrometer_app.utils.config import DEFAULT_SETTINGS
    from utils.camera_settings_utils import get_awb_mode, get_exposure_mode
except ImportError: # Fallback for running script directly
    from spectrometer_app.utils.config import DEFAULT_SETTINGS
    from spectrometer_app.utils.camera_settings_utils import get_awb_mode, get_exposure_mode


def show_instruction_dialog(parent):
    """ Выводит диалоговое окно инструкций """
    # Создаем диалоговое окно
    msg = QMessageBox(parent) 

    # Устанавливаем заголовок окна
    msg.setWindowTitle("Инструкция")

    # Разрешаем использование HTML-форматирования
    msg.setTextFormat(Qt.RichText) 

    # Устанавливаем текст инструкции с HTML-разметкой
    msg.setText("""
    <h3>Инструкция по использованию:</h3>
    <ol>
        <li>Подключите камеру Raspberry Pi Camera Module</li>
        <li>Нажмите 'Сделать снимок' для захвата изображения</li>
        <li>Установите нужную выдержку (в секундах)</li>
        <li>Используйте кнопки 'Вперед'/'Назад' для управления линзами</li>
        <li>Вводите значения положения линз вручную при необходимости</li>
        <li>Регулируйте фокус камеры с помощью соответствующих кнопок</li>
        <li>Используйте меню 'Настройки' для изменения параметров камеры</li>
    </ol>
    """)
    msg.exec_()

def show_settings_dialog(parent):
    """ Выводит диалоговое окно настройки камеры """

    # Создаем диалоговое окно
    dialog = QDialog(parent)

    # Устанавливаем заголовок окна
    dialog.setWindowTitle("Настройки камеры")

    # Фиксируем его размеры
    dialog.setFixedSize(400, 500)

    # Создаем вертикальный layout (компоновка) для основного содержимого
    layout = QVBoxLayout()

    # Временный словарь для хранения виджетов
    widgets = {}

    # Группа настроек яркости
    brightness_group = QGroupBox("Яркость (-1.0 - 1.0)")
    brightness_layout = QHBoxLayout()

    # Создаем слайдер для яркости
    widgets['brightness_slider'] = QSlider(Qt.Horizontal)

    # Устанавливаем диапазон значений слайдера (1, -1) [де-юре (-100, 100)]
    widgets['brightness_slider'].setRange(-100, 100)

    # Устанавливаем текущее значение из настроек
    widgets['brightness_slider'].setValue(int(parent.current_settings['brightness'] * 100))
    brightness_layout.addWidget(widgets['brightness_slider'])

    # Метка для отображения значения
    widgets['brightness_value'] = QLabel(f"{parent.current_settings['brightness']:.2f}")
    brightness_layout.addWidget(widgets['brightness_value'])
    brightness_group.setLayout(brightness_layout)

    # Подключаем сигнал изменения значения слайдера
    widgets['brightness_slider'].valueChanged.connect(lambda v, l=widgets['brightness_value']: l.setText(f"{v / 100.0:.2f}"))
    layout.addWidget(brightness_group) 

    # Аналогичная настройка для контраста, насыщенности и резкости
    for key, name, max_val in [('contrast', 'Контраст', 2.0), 
                               ('saturation', 'Насыщенность', 2.0), ('sharpness', 'Резкость', 2.0)]:
        group = QGroupBox(f"{name} (0.0 - {max_val:.1f})")
        h_layout = QHBoxLayout()

        widgets[f'{key}_slider'] = QSlider(Qt.Horizontal)
        widgets[f'{key}_slider'].setRange(0, int(max_val * 100))
        widgets[f'{key}_slider'].setValue(int(parent.current_settings[key] * 100))
        
        h_layout.addWidget(widgets[f'{key}_slider'])
        widgets[f'{key}_value'] = QLabel(f"{parent.current_settings[key]:.2f}")
        h_layout.addWidget(widgets[f'{key}_value'])

        group.setLayout(h_layout)

        # Подключение сигнала с правильным захватом переменных
        widgets[f'{key}_slider'].valueChanged.connect(lambda v, l=widgets[f'{key}_value'], m=max_val: l.setText(f"{v / 100.0:.2f}"))
        
        layout.addWidget(group)


    """
    Группа настроек баланса белого
    """
    awb_group = QGroupBox("Баланс белого")
    awb_layout = QVBoxLayout()
    widgets['awb_combo'] = QComboBox()
    
    # Варианты баланса белого
    widgets['awb_combo'].addItems(['auto', 
                                   'incandescent', 
                                   'tungsten', 
                                   'fluorescent',
                                   'indoor', 
                                   'daylight', 
                                   'cloudy', 
                                   'custom'])
    
    # Устанавливаем текущее значение
    widgets['awb_combo'].setCurrentText(parent.current_settings['awb_mode'])
    awb_layout.addWidget(widgets['awb_combo'])
    awb_group.setLayout(awb_layout)

    """
    Группа настроек режима экспозиции
    """
    exposure_group = QGroupBox("Режим экспозиции")
    exposure_layout = QVBoxLayout()
    widgets['exposure_combo'] = QComboBox()
        
    # Варианты режима экспозиции
    widgets['exposure_combo'].addItems(['auto', 
                                        'normal', 
                                        'short', 
                                        'long', 
                                        'custom'])

    # Устанавливаем текущее значение
    widgets['exposure_combo'].setCurrentText(parent.current_settings['exposure_mode'])
    exposure_layout.addWidget(widgets['exposure_combo'])
    exposure_group.setLayout(exposure_layout)

    # Добавляем все группы в основной layout
    layout.addWidget(awb_group)
    layout.addWidget(exposure_group)

    # Создаем layout для кнопок
    button_layout = QHBoxLayout()
    apply_btn = QPushButton("Применить")

    # Подключаем обработчик с передачей параметров для кнопок
    apply_btn.clicked.connect(lambda: apply_camera_settings(parent, dialog, widgets))
    reset_btn = QPushButton("Сбросить")
    reset_btn.clicked.connect(lambda: confirm_reset_settings(parent, widgets))
    cancel_btn = QPushButton("Отмена")
    cancel_btn.clicked.connect(dialog.reject)

    # Добавляем кнопки в layout
    button_layout.addWidget(apply_btn)
    button_layout.addWidget(reset_btn)
    button_layout.addWidget(cancel_btn)
    layout.addLayout(button_layout)

    # Устанавливаем layout для диалога
    dialog.setLayout(layout)
    dialog.exec_()


def apply_camera_settings(parent, dialog, widgets):
    """ Функция для применения настроек камеры """
    try:
        # Собираем новые настройки из виджетов
        new_settings = {
            'brightness':    float(widgets['brightness_value'].text()),
            'contrast':      float(widgets['contrast_value'].text()),
            'saturation':    float(widgets['saturation_value'].text()),
            'sharpness':     float(widgets['sharpness_value'].text()),
            'awb_mode':      widgets['awb_combo'].currentText(),
            'exposure_mode': widgets['exposure_combo'].currentText()
        }

        # Обновляем настройки в родительском окне
        parent.current_settings.update(new_settings) 

    except ValueError as e:
         QMessageBox.warning(parent, "Ошибка ввода", f"Неверное значение в настройках: {e}")
         return
    
    # Если камера подключена и доступна
    if parent.camera_connected and parent.camera_thread and hasattr(parent.camera_thread, 'camera'):
        try:
            camera = parent.camera_thread.camera
            
            # Получаем enum-значения для настроек
            awb_mode_enum = get_awb_mode(new_settings['awb_mode'])
            exp_mode_enum = get_exposure_mode(new_settings['exposure_mode'])

            # Применяем настройки к камере
            camera.set_controls({
                'AwbMode':        awb_mode_enum,
                'AeExposureMode': exp_mode_enum,
                'Brightness':     new_settings['brightness'],
                'Contrast':       new_settings['contrast'],
                'Saturation':     new_settings['saturation'],
                'Sharpness':      new_settings['sharpness']
            })
        except Exception as e:
            QMessageBox.warning(parent, "Ошибка", f"Не удалось применить настройки: {e}")

    # Закрываем диалог
    dialog.accept()


def confirm_reset_settings(parent, widgets):
    """ Функция диалогового окна запроса подтверждение сброса """

    # Запрос подтверждения сброса
    reply = QMessageBox.question(
        parent, 'Подтверждение',
        'Вы уверены, что хотите сбросить настройки камеры к значениям по умолчанию?',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )

    # Если пользователь подтвердил сброс
    if reply == QMessageBox.Yes:
        # Подготавливаем значения по умолчанию
        defaults_to_reset = {
            'brightness':    DEFAULT_SETTINGS['brightness'],
            'contrast':      DEFAULT_SETTINGS['contrast'],
            'saturation':    DEFAULT_SETTINGS['saturation'],
            'sharpness':     DEFAULT_SETTINGS['sharpness'],
            'awb_mode':      DEFAULT_SETTINGS['awb_mode'],
            'exposure_mode': DEFAULT_SETTINGS['exposure_mode']
        }

        # Обновляем настройки в родительском окне
        parent.current_settings.update(defaults_to_reset)

        # Обновляем UI элементы в диалоге
        widgets['brightness_slider'].setValue(int(defaults_to_reset['brightness'] * 100))
        widgets['contrast_slider'].setValue(int(defaults_to_reset['contrast'] * 100))
        widgets['saturation_slider'].setValue(int(defaults_to_reset['saturation'] * 100))
        widgets['sharpness_slider'].setValue(int(defaults_to_reset['sharpness'] * 100))
        widgets['awb_combo'].setCurrentText(defaults_to_reset['awb_mode'])
        widgets['exposure_combo'].setCurrentText(defaults_to_reset['exposure_mode'])

        # Применяем настройки по умолчанию к камере
        if parent.camera_connected and parent.camera_thread and hasattr(parent.camera_thread, 'camera'):
            try:
                camera = parent.camera_thread.camera
                awb_mode_enum = get_awb_mode(DEFAULT_SETTINGS['awb_mode'])
                exp_mode_enum = get_exposure_mode(DEFAULT_SETTINGS['exposure_mode'])

                camera.set_controls({
                    'AwbMode':        awb_mode_enum,
                    'AeExposureMode': exp_mode_enum,
                    'Brightness':     DEFAULT_SETTINGS['brightness'],
                    'Contrast':       DEFAULT_SETTINGS['contrast'],
                    'Saturation':     DEFAULT_SETTINGS['saturation'],
                    'Sharpness':      DEFAULT_SETTINGS['sharpness']
                })
            except Exception as e:
                QMessageBox.warning(parent, "Ошибка", f"Не удалось сбросить настройки: {e}")