# spectrometer_app/core/camera_thread.py

import os
import time
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage
from picamera2 import Picamera2
import numpy as np

try:
    from spectrometer_app.utils.config import DEFAULT_SETTINGS
    from utils.camera_settings_utils import (
        restore_camera_settings_from_qsettings,
        apply_full_ui_settings_to_camera,
        set_camera_focus,
        update_specific_camera_settings,
        save_camera_metadata,
        restore_last_camera_settings
    )

# Резервный вариант для непосредственного запуска скрипта
except ImportError: 
    from spectrometer_app.utils.config import DEFAULT_SETTINGS
    from spectrometer_app.utils.camera_settings_utils import (
        restore_camera_settings_from_qsettings,
        apply_full_ui_settings_to_camera,
        set_camera_focus,
        update_specific_camera_settings,
        save_camera_metadata,
        restore_last_camera_settings
    )


class CameraThread(QThread):

    # Сигналы для передачи изменений в основной поток
    change_pixmap    = pyqtSignal(QImage) # для обновления изображения
    camera_error     = pyqtSignal()       # для уведомления об ошибке камеры
    settings_updated = pyqtSignal(dict)   # для уведомления об обновлении настроек

    def __init__(self, settings_manager):
        super().__init__()
        self.camera           = None             # переменная потока камеры
        self.running          = True             # флаг работы потока (работает/нет)
        self.settings_manager = settings_manager # настройки
        self.no_camera_image  = self._load_no_camera_image()  

        """
        Внутреннее состояние для фокуса/экспозиции, 
        обновляется методами-обертками
        """
        self.current_settings_state = {
            'focus': self.settings_manager.value('focus', DEFAULT_SETTINGS['focus'], type=int),
            'exposure': self.settings_manager.value('exposure', DEFAULT_SETTINGS['exposure'], type=float)
        }

        # Переменная для сохранения настроек при смене режима камеры
        self.last_metadata_settings = {} 

    def _load_no_camera_image(self):        
        """Загрузка изображения-заглушки для случая отсутствия камеры"""

        image         = QImage()
        resource_path = os.path.join(os.path.dirname(__file__), '../resources/no_camera_image.jpg')

        # Если заглушки нет, выводим белое изображение
        if os.path.exists(resource_path):
            image.load(resource_path)
        else:
            print(f"Warning: Placeholder image not found at {resource_path}")
            image = QImage(711, 530, QImage.Format_RGB888)
            image.fill(Qt.white)

        return image

    def run(self):
        """Работа камеры, работает постоянно"""

        try:
            # Включение обхода кэша глифов
            os.environ["QT_ENABLE_GLYPH_CACHE_WORKAROUND"] = "1" 

            # Отключение логирования для компонентов QPA
            os.environ["QT_LOGGING_RULES"] = "qt.qpa.*=false"

            self.camera = Picamera2()   # экземпляр камеры

            config = self.camera.create_video_configuration(
                main   = {"size": (1280, 720), "format": "RGB888"},
                encode = "main",         # указание основного кодирования
                queue  = False           # отключение очереди (для оптимизации)
            )

            self.camera.configure(config)   # применение конфигурации к камере

            # Восстановление базовых настроек камеры из QSettings
            restore_camera_settings_from_qsettings(self.camera, self.settings_manager)

            self.camera.start()

            # Захват изображения каждые 30 мс (~33 к/c)
            while self.running:
                self._capture_frame()
                QThread.msleep(30)

        except Exception as e:
            print(f"Failed to initialize camera: {e}")
            self.camera_error.emit()
        finally:

            # Проверка, инициализирована ли камера
            if hasattr(self, 'camera') and self.camera is not None:
                if self.camera.started:
                    try: 
                        self.camera.stop()
                    except Exception as e_stop: 
                        print(f"Error stopping camera in run finally: {e_stop}")
                try: 
                    self.camera.close()
                except Exception as e_close: 
                    print(f"Error closing camera in run finally: {e_close}")

            self.camera = None  # Обнуление ссылки на камеру

    def _capture_frame(self):
        """Захватывает кадр в rgb формате"""

        if not self.camera or not self.camera.started:
            return
        
        try:
            # Захват кадра с камеры и сохранение его в массиве.
            array = self.camera.capture_array("main")

            """
            Если захваченный кадр имеет 3 канала (RGB), то
            нужно поменять местами каналы B и R для правильного отображения.
            """
            if array.shape[2] == 3:
                array[:, :, [0, 2]] = array[:, :, [2, 0]]   # BGR -> RGB

            # Получение высоты (h), ширины (w) и кол-ва каналов (ch) из массива
            h, w, ch = array.shape

            # Создание изображения QImage из массива данных
            qt_image = QImage(array.data, w, h, ch * w, QImage.Format_RGB888)

            self.change_pixmap.emit(qt_image)   # обновляет изображение в UI
        
        except Exception as e:
            print(f"Camera capture error: {e}")
            self.camera_error.emit()    # сигнал ошибки каамеры
            self.running = False        # завершение работы

    """
    ----------------------------------------------------
    --- Обертки методов для вызова утилитных функций ---
    ----------------------------------------------------
    """
    def apply_full_ui_settings(self, ui_settings):
        applied_state = apply_full_ui_settings_to_camera(self.camera, ui_settings)

        # Если настройки были применены
        if applied_state:
            # Обновление внутреннего состояния фокуса и экспозиции
            if 'focus' in applied_state:
                self.current_settings_state['focus'] = applied_state['focus']
            if 'exposure' in applied_state:
                self.current_settings_state['exposure'] = applied_state['exposure']
            # Cигнала для обновления состояния настроек.
            self.settings_updated.emit(self.current_settings_state.copy())

    def set_focus(self, distance_mm):
        success = set_camera_focus(self.camera, distance_mm)
        if success:
            # Обновление внутреннего состояния фокуса
            self.current_settings_state['focus'] = distance_mm
            # Сигнал для обновления состояния настроек
            self.settings_updated.emit(self.current_settings_state.copy())
        return success

    def update_settings(self, settings_dict):
        applied_state = update_specific_camera_settings(self.camera, settings_dict)
        if applied_state:
            # Обновление внутреннего состояния фокуса и экспозиции
            if 'focus' in applied_state:
                self.current_settings_state['focus'] = applied_state['focus']
            if 'exposure' in applied_state:
                self.current_settings_state['exposure'] = applied_state['exposure']
            # Сигнал для обновления состяния настроек
            self.settings_updated.emit(self.current_settings_state.copy())

    def save_current_settings(self):
        # Сохранение текущих настроек камеры.
        self.last_metadata_settings = save_camera_metadata(self.camera, self.current_settings_state)
        return self.last_metadata_settings

    def restore_last_settings(self):
        # Восстановление последних сохраненных настроек камеры.  
        restore_last_camera_settings(self.camera, self.last_metadata_settings)

    ''' 
    ---------------------------
    --- Обертки закончились ---
    ---------------------------
    '''

    def stop(self):
        self.running = False
        self.wait() # Ждет run() для завершения
