# spectrometer_app/ui/event_handlers.py

from PyQt5.QtWidgets import QMessageBox

def update_settings_from_camera(app_instance, camera_settings):
    """Обновление UI при изменении настроек из потока камеры"""

    # Проверка наличия настроек экспозиции и соответствующего поля ввода
    if 'exposure' in camera_settings and hasattr(app_instance, 'exposure_input') and \
       abs(camera_settings['exposure'] - app_instance.current_settings['exposure']) > 1e-6:
        # Обновление текущих настроек и текстового поля
        app_instance.current_settings['exposure'] = camera_settings['exposure']
        app_instance.exposure_input.setText(f"{camera_settings['exposure']:.1f}")

    # Проверка наличия настроек фокуса и соответствующего поля ввода
    if 'focus' in camera_settings and hasattr(app_instance, 'focus_input') and \
       camera_settings['focus'] != app_instance.current_settings['focus']:
        # Обновление текущих настроек и текстового поля
        app_instance.current_settings['focus'] = camera_settings['focus']
        app_instance.focus_input.setText(str(camera_settings['focus']))


def change_exposure(app_instance, delta):
    """ Изменение выдержки с помощью кнопок +/- """
    if not hasattr(app_instance, 'exposure_input'): 
        return
    
    try:
        current_value_str = app_instance.exposure_input.text()

        # Получение текущего значения с обработкой ошибок
        try:
            current_value = float(current_value_str)
        except ValueError:
            current_value = app_instance.current_settings.get('exposure', 1.0) # Значение по умолчанию

        # Расчет нового значения с ограничением диапазона
        new_value = current_value + delta
        new_value = max(0.1, min(30.0, new_value)) # ограничение
        
        # Обновление настроек и интерфейса
        app_instance.current_settings['exposure'] = round(new_value, 1)
        app_instance.exposure_input.setText(f"{app_instance.current_settings['exposure']:.1f}")

        # Отправка новых настроек в поток камеры
        if app_instance.camera_connected and app_instance.camera_thread:
            app_instance.camera_thread.update_settings({'exposure': app_instance.current_settings['exposure']})
    except ValueError:
        print("Invalid value in exposure input during change.")
    except Exception as e:
        print(f"Error changing exposure: {e}")


def update_exposure(app_instance):
    """ Обновление выдержки из поля ввода """

    if not hasattr(app_instance, 'exposure_input'): 
        return
    
    try:
        # Парсинг значения и проверка диапазона
        value = float(app_instance.exposure_input.text())
        app_instance.current_settings['exposure'] = max(0.1, min(30.0, value)) 

        # Обновление поля ввода (форматирование и округление)
        app_instance.exposure_input.setText(f"{round(app_instance.current_settings['exposure'], 1):.1f}")

        # Отправка новых настроек в поток камеры
        if app_instance.camera_connected and app_instance.camera_thread:
            app_instance.camera_thread.update_settings({'exposure': app_instance.current_settings['exposure']})
            
    except ValueError:
        # Восстановление предыдущего значения при ошибке
        last_good_value = app_instance.current_settings.get('exposure', 1.0)
        app_instance.exposure_input.setText(f"{round(last_good_value, 1):.1f}")
        print("Invalid value entered for exposure.")
    except Exception as e:
        print(f"Error updating exposure: {e}")


def change_focus(app_instance, delta_mm):
    """ Изменение фокуса с помощью кнопок +/- """

    if not hasattr(app_instance, 'focus_input'):
        return
    
    try:
        current_mm_str = app_instance.focus_input.text()

        # Получение текущего значения с обработкой ошибок
        try:
            current_mm = int(current_mm_str)
        except ValueError:
            current_mm = app_instance.current_settings.get('focus', 1000) # Значение по умолчанию

        # Расчет нового значения с ограничением диапазона
        new_mm = max(10, min(10000, current_mm + delta_mm)) # значение по умолчанию
        app_instance.focus_input.setText(str(new_mm))
        update_focus(app_instance) # Вызов функции обновления

    except ValueError:
        print("Invalid value in focus input during change.")

    except Exception as e:
        print(f"Error changing focus: {e}")


def update_focus(app_instance):
    """ Обновление фокуса из поля ввода """
    if not hasattr(app_instance, 'focus_input'): 
        return
    
    try:
        # Парсинг значения и проверка диапазона
        distance_mm = int(app_instance.focus_input.text())
        
        if not (10 <= distance_mm <= 10000):
            # Восстановление предыдущего значения при ошибке
            last_good_value = app_instance.current_settings.get('focus', 1000)
            app_instance.focus_input.setText(str(last_good_value))
            raise ValueError("Диапазон фокуса: 10-10000 мм")
        
        # Обновление настроек
        app_instance.current_settings['focus'] = distance_mm
        
        # Отправка новых настроек в поток камеры
        if app_instance.camera_connected and app_instance.camera_thread:
             success = app_instance.camera_thread.set_focus(distance_mm)

             if not success:
                 # Показ предупреждения при ошибке
                 QMessageBox.warning(app_instance, "Ошибка Камеры", "Не удалось установить фокус на камере.")

    except ValueError as e:
        print(f"Ошибка валидации фокуса: {e}")
        QMessageBox.warning(app_instance, "Ошибка Ввода", f"Неверное значение фокуса: {e}")

    except Exception as e:
        print(f"Непредвиденная ошибка фокусировки: {e}")
        QMessageBox.critical(app_instance, "Критическая ошибка", f"Ошибка при установке фокуса: {e}")


def change_lens_pos(app_instance, lens_num, delta):
    """Изменение положения линзы кнопками +/- (симуляция)"""

    # Определение атрибутов в зависимости от номера линзы
    input_attr = 'lens1_pos_input' if lens_num == 1 else 'lens2_pos_input'
    setting_key = 'lens1_pos' if lens_num == 1 else 'lens2_pos'

    if not hasattr(app_instance, input_attr): return

    input_widget = getattr(app_instance, input_attr)
    try:
        current_val_str = input_widget.text()

        # Получение текущего значения с обработкой ошибок
        try:
            current_val = int(current_val_str)
        except ValueError:
            current_val = app_instance.current_settings.get(setting_key, 0)  # Значение по умолчанию

        # Расчет нового значения
        new_val = current_val + delta

        # Обновление настроек и интерфейса
        app_instance.current_settings[setting_key] = new_val
        input_widget.setText(str(new_val))
        
        print(f"Lens {lens_num} position changed to: {new_val} (Simulated)")

    except ValueError:
        print(f"Invalid value in lens {lens_num} input during change.")

    except Exception as e:
        print(f"Error changing lens {lens_num} position: {e}")


def update_lens_pos(app_instance, lens_num):
    """Обновление положения линзы из поля ввода (симуляция)"""

    # Определение атрибутов в зависимости от номера линзы
    input_attr = 'lens1_pos_input' if lens_num == 1 else 'lens2_pos_input'
    setting_key = 'lens1_pos' if lens_num == 1 else 'lens2_pos'

    if not hasattr(app_instance, input_attr): 
        return

    input_widget = getattr(app_instance, input_attr)

    try:
        # Парсинг значения и обновление настроек
        value = int(input_widget.text())
        app_instance.current_settings[setting_key] = value
        print(f"Lens {lens_num} position set to: {value} (Simulated)")

    except ValueError:
        # Восстановление предыдущего значения при ошибке
        last_good_value = app_instance.current_settings.get(setting_key, 0)
        input_widget.setText(str(last_good_value))
        print(f"Invalid value entered for lens {lens_num} position.")

    except Exception as e:
        print(f"Error updating lens {lens_num} position: {e}")

# Обертки для удобного вызова функций для конкретных линз
def update_lens1_pos(app_instance):
    update_lens_pos(app_instance, 1)

def update_lens2_pos(app_instance):
    update_lens_pos(app_instance, 2)