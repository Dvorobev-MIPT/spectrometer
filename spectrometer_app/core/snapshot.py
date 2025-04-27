# spectrometer_app/core/snapshot.py

import os
import time
import traceback
from PyQt5.QtWidgets import QMessageBox
from picamera2 import Picamera2
from libcamera import controls, Transform


try:
    from utils.camera_settings_utils import get_awb_mode
except ImportError: # Fallback for running script directly
    from spectrometer_app.utils.camera_settings_utils import get_awb_mode



def take_and_save_snapshot_standalone(parent_window):
    """
    Обрабатывает логику создания и сохранения снимков в форматах TIFF и RAW.
    Принимает в качестве входного параметра главный экземпляр CameraApp.
    """
    if not parent_window.camera_connected or not parent_window.camera_thread:
        QMessageBox.warning(parent_window, "Ошибка", "Камера не подключена или поток не запущен!")
        return

    capture_cam = None # переменная камеры

    # текущее состояние камеры
    original_running_state = parent_window.camera_thread.isRunning()

    # текущие настройки камеры
    snapshot_settings = parent_window.current_settings.copy()

    video_controls = {} # Словарь для хранения параметров видео

    # Если поток работает и камера доступна, сохраняем текущие настройки
    if original_running_state and parent_window.camera_thread.camera:
         video_controls = parent_window.camera_thread.save_current_settings()
    else:
         print("Warning: Could not get live camera metadata for snapshot.")

    try:
        results_dir = os.path.abspath("./results") # Директория для результатов
        os.makedirs(results_dir, exist_ok=True)

       # Получение времени экспозиции из настроек
        exposure_time = snapshot_settings['exposure']

        # Если поток камеры был запущен, останавливаем его для создания снимка
        if original_running_state:
            # Ожидание остановки потока (1 секунда)
            parent_window.camera_thread.stop()
            if not parent_window.camera_thread.wait(1000):
                print("Warning: Camera thread did not stop gracefully for snapshot.")
            # Отключение сигналов от потока камеры
            try: 
                parent_window.camera_thread.change_pixmap.disconnect(parent_window.set_image)
            except TypeError: 
                pass
            try: 
                parent_window.camera_thread.camera_error.disconnect(parent_window.handle_camera_error)
            except TypeError: 
                pass
            try: 
                parent_window.camera_thread.settings_updated.disconnect(parent_window.update_settings_from_camera_wrapper)
            except TypeError: 
                pass

        capture_cam = Picamera2() # включаем камеру

        try:
            # доступные режимы сенсора
            sensor_modes = capture_cam.sensor_modes

            # Фильтрация режимов с глубиной цвета >= 10 бит (нужно для обработки)
            valid_modes = [m for m in sensor_modes if m.get('bit_depth', 0) >= 10]

            # Используем все режимы, если нет подходящих
            if not valid_modes: 
                valid_modes = sensor_modes
            
            # Выбор режима с максимальным разрешением
            best_mode = max(valid_modes, key=lambda m: m['size'][0] * m['size'][1])
            max_res = best_mode['size']
            print(f"Selected max resolution: {max_res} from mode: {best_mode}")

        # В случае ошибки используем разрешение по умолчанию
        except Exception as e_res:
            print(f"Could not determine max resolution, using default (1920, 1080). Error: {e_res}")
            max_res = (1920, 1080)

        # Создание конфигурации для снимка
        still_config = capture_cam.create_still_configuration(
            main         = {"size": max_res, "format": "RGB888"},
            raw          = {"size": max_res},  # RAW данные
            buffer_count = 2,                  # Количество буферов
            transform    = video_controls.get("Transform", Transform())
        )
        # Применение конфигурации
        capture_cam.configure(still_config)

        # Настройка камеры и ее запуск
        awb_mode_enum = get_awb_mode(snapshot_settings['awb_mode'])

        controls_to_set = {
            'ExposureTime':       int(exposure_time * 1000000),
            'AfMode':             controls.AfModeEnum.Manual,
            'LensPosition':       1.0 / (snapshot_settings['focus'] / 1000.0),
            'AwbMode':            awb_mode_enum, 'AeEnable': False,
            'Brightness':         snapshot_settings['brightness'],
            'Contrast':           snapshot_settings['contrast'],
            'Saturation':         snapshot_settings['saturation'],
            'Sharpness':          snapshot_settings['sharpness'],
            'NoiseReductionMode': video_controls.get('NoiseReductionMode', controls.draft.NoiseReductionModeEnum.Off)
        }

        capture_cam.set_controls(controls_to_set)
        capture_cam.start()
        time.sleep(1)

        # Генерация имен файлов формата YYYY-MM-DD_HH-MM-SS
        timestamp    = time.strftime("%Y-%m-%d_%H-%M-%S")
        rgb_filename = os.path.join(results_dir, f"{timestamp}.tiff")
        raw_filename = os.path.join(results_dir, f"{timestamp}.raw") 

        request = None # Переменнаая для запроса снимка

        try:
            # Захват снимка
            request = capture_cam.capture_request()
            
            # Сохранение TIFF изображения максимального качества
            print("Saving TIFF image...")
            rgb_image = request.make_image("main")
            rgb_image.save(rgb_filename, quality=100)
            print(f"TIFF saved: {rgb_filename}")

            # Сохранение RAW данных
            print("Saving raw sensor data...")
            raw_data = request.make_array("raw")
            raw_data.tofile(raw_filename)
            print(f"Raw data saved: {raw_filename}")

            # Вывод сообщения об успешном сохранении
            saved_files_msg = (f"RGB: {os.path.basename(rgb_filename)}\n"
                               f"RAW: {os.path.basename(raw_filename)}")
            QMessageBox.information(parent_window, "Успех", f"Изображения сохранены:\n{saved_files_msg}")

        except Exception as save_err:
            """
            Отлавливание ошибки при
                1. создании изображения;
                2. сохранении; 
                3. создании массива данных;
                4. в файле.
            """
            print(f"ERROR during image saving: {save_err}")
            traceback.print_exc() # Печать tb стека
            QMessageBox.critical(parent_window, "Ошибка Сохранения", f"Не удалось сохранить файлы: {save_err}")

        finally:
             # если потребуется - освободим ресурсы
             if request:
                request.release()

    except Exception as e:
        # Обработка общих ошибок
        error_details = traceback.format_exc()
        print(f"Snapshot Error details: {error_details}")
        QMessageBox.critical(parent_window, "Ошибка", f"Не удалось сохранить снимок: {str(e)}")
    finally:
        # Завершение работы с камерой
        if capture_cam is not None:
            if capture_cam.started:
                try: 
                    capture_cam.stop() # Остановка камеры
                except Exception as e_stop: 
                    print(f"Error stopping capture camera: {e_stop}")
            try: 
                capture_cam.close()    # Закрытие камеры
            except Exception as e_close: 
                print(f"Error closing capture camera: {e_close}")

        # Восстановление исходного состояния потока камеры
        if original_running_state:
            print("Restarting video thread...")
            # Перезапуск камеры через родительское окно
            parent_window.initCamera()
        else:
             print("Video thread was not running, not restarting.")