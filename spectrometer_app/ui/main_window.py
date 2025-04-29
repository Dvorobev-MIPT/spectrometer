# spectrometer_app/ui/main_window.py

import sys
import os
import time
import traceback 
import subprocess
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QMessageBox
from PyQt5.QtCore import Qt, QTimer, QSettings
from PyQt5.QtGui import QPixmap
from picamera2 import Picamera2
from libcamera import controls, Transform
try:
    from utils.config import DEFAULT_SETTINGS
    from core.camera_thread import CameraThread
    from ui_setup import (setup_styles, create_menu_bar, setup_video_panel,
                           setup_control_panel, set_window_icon)
    from dialogs import show_instruction_dialog, show_settings_dialog
    from utils.camera_settings_utils import get_awb_mode
    from core.snapshot import take_and_save_snapshot_standalone
    from utils.event_handlers import (
        update_settings_from_camera,
        change_exposure, update_exposure,
        change_focus, update_focus,
        change_lens_pos, update_lens1_pos, update_lens2_pos
    )

except ImportError: # Fallback
    from spectrometer_app.utils.config import DEFAULT_SETTINGS
    from spectrometer_app.core.camera_thread import CameraThread
    from spectrometer_app.ui.ui_setup import (setup_styles, create_menu_bar, setup_video_panel,
                           setup_control_panel, set_window_icon)
    from spectrometer_app.ui.dialogs import show_instruction_dialog, show_settings_dialog
    from spectrometer_app.utils.camera_settings_utils import get_awb_mode
    from spectrometer_app.core.snapshot import take_and_save_snapshot_standalone
    # Import the new event handler functions (fallback path)
    from spectrometer_app.utils.event_handlers import (
        update_settings_from_camera,
        change_exposure, update_exposure,
        change_focus, update_focus,
        change_lens_pos, update_lens1_pos, update_lens2_pos
    )


class CameraApp(QMainWindow):
    """ Основной класс приложения, по сути класс основного окна """
    def __init__(self):
        super().__init__()      # инициализация родительского класса
        self.setWindowTitle("Спектрометр")      # заголовок окна
        self.setGeometry(100, 100, 1200, 490)   # размер и положение окна

        # Инициализация настроек приложения
        self.settings = QSettings("MyCompany", "SpectrometerApp")
        self.current_settings = DEFAULT_SETTINGS.copy()

        # Переменных состояния
        self.current_frame    = None       # текущий кадр
        self.camera_connected = False      # флаг подключения камеры
        self.camera_thread    = None       # поток управления камерой

        self.initUI()       # Инициализация интерфейса
        self.initCamera()   # Инициализация камеры

    def _load_settings(self):
        """Загрузка сохраненных настроек из QSettings"""
        settings_dict = DEFAULT_SETTINGS.copy() # Копия настроек по умолчанию

        for key in settings_dict:
            value_type = type(DEFAULT_SETTINGS.get(key, ""))

            # Загрузка значений с учетом их типа
            if value_type is float:
                 settings_dict[key] = self.settings.value(key, DEFAULT_SETTINGS[key], type=float)
            elif value_type is int:
                 settings_dict[key] = self.settings.value(key, DEFAULT_SETTINGS[key], type=int)
            else:
                 settings_dict[key] = self.settings.value(key, DEFAULT_SETTINGS[key])
        return settings_dict

    def _save_settings(self):
        """Сохранение текущих настроек в QSettings"""
        for key, value in self.current_settings.items():
            self.settings.setValue(key, value)

    def initUI(self):
        """Инициализация пользовательского интерфейса."""
        setup_styles(self)                      # Установка стилей
        create_menu_bar(self)                   # Создание меню
        central_widget = QWidget()              # Центральный виджет
        self.setCentralWidget(central_widget)   
        main_layout = QHBoxLayout(central_widget)       # Основной горизонтальный layout
        main_layout.setContentsMargins(10, 10, 10, 10)  # Отступы
        main_layout.setSpacing(15)              # Расстояние между элементами
        setup_video_panel(self, main_layout)    # Настройка панели видео
        setup_control_panel(self, main_layout)  # Настройка панели управления
        set_window_icon(self)                   # Установка иконки окна

    def initCamera(self):
        """Инициализация или ре-инициализация камеры в отдельном потоке."""

        # Остановка существующего потока камеры, если он запущен
        if self.camera_thread and self.camera_thread.isRunning():
            print("Stopping existing camera thread before re-init...")
            self.camera_thread.stop()
            if not self.camera_thread.wait(2000):
                print("Warning: Existing camera thread did not stop gracefully.")

            # Отключение сигналов
            try: 
                self.camera_thread.change_pixmap.disconnect(self.set_image)
            except TypeError: 
                pass
            try: 
                self.camera_thread.camera_error.disconnect(self.handle_camera_error)
            except TypeError: 
                pass
            try: 
                self.camera_thread.settings_updated.disconnect(self.update_settings_from_camera_wrapper)
            except TypeError: 
                pass

        print("Initializing new camera thread...")

        # Создание нового потока камеры
        self.camera_thread = CameraThread(self.settings)

        # Подключение сигналов
        self.camera_thread.change_pixmap.connect(self.set_image)
        self.camera_thread.camera_error.connect(self.handle_camera_error)
        self.camera_thread.settings_updated.connect(self.update_settings_from_camera_wrapper)
        self.camera_thread.start()
    
        # Отложенное применение настроек
        QTimer.singleShot(500, lambda: self.camera_thread.apply_full_ui_settings(self.current_settings))

    def set_image(self, image):
        """Отображение кадра с камеры в интерфейсе"""

        # Пропуск кадра, если окно не активно
        if not self.isVisible() or self.isMinimized(): 
            return
        
        self.current_frame = image          # сохранение текущего кадра
        self.camera_connected = True        # установка флага подключения
        pixmap = QPixmap.fromImage(image)   # преобразование в QPixmap

        if hasattr(self, 'video_label'):
            # Масштабирование и отображение изображения
            self.video_label.setPixmap(pixmap.scaled(
                self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))

    def handle_camera_error(self):
        """Обработка ошибки инициализации/работы камеры."""
        
        self.camera_connected = False # Сброс флага подключения

        """
        Проверяем, существует ли поток камеры и есть ли у него атрибут 
        no_camera_image, а также существует ли виджет video_label
        """
        if hasattr(self, 'camera_thread') and self.camera_thread is not None and \
           hasattr(self.camera_thread, 'no_camera_image') and \
           self.camera_thread.no_camera_image is not None and \
           not self.camera_thread.no_camera_image.isNull() and \
           hasattr(self, 'video_label'):
            
            try:
                pixmap = QPixmap.fromImage(self.camera_thread.no_camera_image)
                self.video_label.setPixmap(pixmap.scaled(
                    self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
                # Очищаем текст, если он был установлен ранее
                self.video_label.setText("") 
                
            except Exception as e:
                print(f"Error displaying placeholder image: {e}")
                # Если произошла ошибка при отображении картинки, показываем текст
                if hasattr(self, 'video_label'):
                    self.video_label.setText("Ошибка отображения заглушки")

        elif hasattr(self, 'video_label'):
            # Если условие выше не выполнено, просто устанавливаем текст
            self.video_label.setText("Камера не подключена")
        
        # Дополнительно выводим сообщение в консоль для отладки
        print("Camera error handled. Placeholder image should be displayed if available.")

    """
    -------------------------
    --- Оберточные методы ---
    -------------------------
    """
    def update_settings_from_camera_wrapper(self, camera_settings):
        """Needed because signal connection cannot directly call function needing 'self'."""
        update_settings_from_camera(self, camera_settings)

    def change_exposure(self, delta):
        change_exposure(self, delta)

    def update_exposure(self):
        update_exposure(self)

    def change_focus(self, delta_mm):
        change_focus(self, delta_mm)

    def update_focus(self):
        update_focus(self)

    def change_lens_pos(self, lens_num, delta):
        change_lens_pos(self, lens_num, delta)

    def update_lens1_pos(self):
        update_lens1_pos(self)

    def update_lens2_pos(self):
        update_lens2_pos(self)

    def show_instruction_dialog(self):
        show_instruction_dialog(self)

    def show_settings_dialog(self):
        show_settings_dialog(self)

    def take_and_save_snapshot(self):
        take_and_save_snapshot_standalone(self)
        
    def open_results_folder(self):
        """Открывает папку с результатами в файловом менеджере"""
        results_dir = os.path.abspath("./results")
        if not os.path.exists(results_dir):
            os.makedirs(results_dir, exist_ok=True)
        try:
            if sys.platform.startswith('darwin'):
                subprocess.Popen(['open', results_dir])
            elif os.name == 'nt':
                os.startfile(results_dir)
            elif os.name == 'posix':
                subprocess.Popen(['xdg-open', results_dir])
            else:
                QMessageBox.warning(self, "Ошибка", f"Не удалось определить способ открытия папки для вашей ОС.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть папку результатов:\n{e}")

    # --- Переопределенные методы Qt ---
    def resizeEvent(self, event):
        """Обработка изменения размера окна"""
        if self.camera_connected and self.current_frame:
            self.set_image(self.current_frame)  # Обновление изображения
        elif not self.camera_connected:
             self.handle_camera_error()         # Обработка состояния без камеры
        super().resizeEvent(event)              # Вызов родительского метода

    def closeEvent(self, event):
        """Обработка закрытия окна"""

        self._save_settings() # Сохранение настроек

        # Остановка потока камеры
        if hasattr(self, 'camera_thread') and self.camera_thread.isRunning():
            self.camera_thread.stop()
            if not self.camera_thread.wait(2000):
                 print("Warning: Camera thread did not stop gracefully on close.")

        event.accept() # закрытие окна

