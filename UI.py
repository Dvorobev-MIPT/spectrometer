import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QGroupBox, QMenuBar, QAction,
                             QDialog, QScrollArea, QMessageBox, QComboBox, QFrame, QSlider)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QImage, QPixmap, QIntValidator, QFont, QDoubleValidator, QIcon
import numpy as np
from picamera2 import Picamera2
from libcamera import controls
import time


class CameraThread(QThread):
    change_pixmap = pyqtSignal(QImage)
    camera_error = pyqtSignal()
    settings_updated = pyqtSignal(dict)  # Для синхронизации настроек

    def __init__(self):
        super().__init__()
        self.camera = None
        self.running = True
        self.no_camera_image = QImage()
        if os.path.exists("./resources/no_camera.png"):
            self.no_camera_image.load("./resources/no_camera.png")
        else:
            # Create a blank white image as fallback
            self.no_camera_image = QImage(800, 600, QImage.Format_RGB888)
            self.no_camera_image.fill(Qt.white)
        
        self.current_settings = {
            'focus': 1000,
            'exposure': 3.0
        }

    def run(self):
        try:
            self.camera = Picamera2()
            config = self.camera.create_preview_configuration(
                main={"size": (1280, 720), "format": "RGB888"}
            )
            self.camera.configure(config)
            self.camera.start()
                
            while self.running:
                try:
                    array = self.camera.capture_array("main")
                    
                    if array.shape[2] == 3:  # If 3 channels
                        rgb_image = array.copy()
                        rgb_image[:, :, [0, 2]] = rgb_image[:, :, [2, 0]]  # Swap R and B
                    else:
                        rgb_image = array
                    
                    h, w, ch = rgb_image.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    self.change_pixmap.emit(qt_image)
                except Exception as e:
                    print(f"Camera capture error: {e}")
                    self.camera_error.emit()
                    break
                QThread.msleep(30)
        except Exception as e:
            print(f"Failed to initialize camera: {e}")
            self.camera_error.emit()
        finally:
            if hasattr(self, 'camera') and self.camera is not None:
                self.camera.stop()
                self.camera.close()

    def set_focus(self, distance_mm):
        """Установка ручного фокуса в миллиметрах"""
        try:
            lens_position = 1.0 / (distance_mm / 1000.0)
            self.camera.set_controls({
                "AfMode": controls.AfModeEnum.Manual,
                "LensPosition": lens_position
            })
            return True
        except Exception as e:
            print(f"Focus error: {e}")
            return False
    
    def update_settings(self, settings):
        """Обновление настроек камеры"""
        if self.camera is not None:
            try:
                if 'focus' in settings:
                    self.current_settings['focus'] = settings['focus']
                    # Здесь должна быть реализация изменения фокуса камеры
                    # Например: self.camera.set_controls({'AfMode': controls.AfModeEnum.Manual, 'LensPosition': settings['focus']})
                
                if 'exposure' in settings:
                    self.current_settings['exposure'] = settings['exposure']
                    # Здесь должна быть реализация изменения выдержки камеры
                    # Например: self.camera.set_controls({'ExposureTime': int(settings['exposure'] * 1000000)})
                
                self.settings_updated.emit(self.current_settings)
            except Exception as e:
                print(f"Failed to update camera settings: {e}")

    def save_current_settings(self):
        """Сохраняет текущие настройки камеры"""
        if self.camera is None:
            return {}
            
        try:
            controls = self.camera.camera_controls
            current_values = self.camera.capture_metadata().get("Controls", {})
            
            saved_settings = {}
            for control in controls:
                if control in current_values:
                    saved_settings[control] = current_values[control]
            
            return saved_settings
        except Exception as e:
            print(f"Error saving camera settings: {e}")
            return {}
    
    # В методе restore_settings класса CameraThread
    def restore_settings(self, settings):
        """Восстанавливает настройки камеры"""
        if self.camera is None or not settings:
            return
            
        try:
            # Получаем список доступных контролов
            available_controls = self.camera.camera_controls
            
            controls_to_set = {}
            for control, value in settings.items():
                # Проверяем, что контроль доступен и значение в допустимом диапазоне
                if control in available_controls:
                    control_info = available_controls[control]
                    min_val, max_val = control_info.min, control_info.max
                    
                    # Проверяем, что значение в допустимом диапазоне
                    if min_val <= value <= max_val:
                        controls_to_set[control] = value
                    else:
                        print(f"Value {value} for {control} is out of range ({min_val}-{max_val})")
            
            if controls_to_set:
                self.camera.set_controls(controls_to_set)
        except Exception as e:
            print(f"Error restoring camera settings: {e}")

    def stop(self):
        self.running = False
        if self.camera:
            self.camera.stop()
        self.wait()


class CameraApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Спектрометр")
        self.setGeometry(100, 100, 1200, 600)
        
        # Set window icon
        if os.path.exists("./resources/icon.png"):
            self.setWindowIcon(QIcon("./resources/icon.png"))

        # Default camera settings
        self.default_settings = {
            'brightness': 0.5,
            'contrast': 1.0,
            'saturation': 1.0,
            'sharpness': 1.0,
            'awb_mode': 'auto',
            'exposure_mode': 'auto',
            'focus': 50,      # in mm
            'exposure': 3.0   # in seconds
        }
        self.current_settings = self.default_settings.copy()

        # Lens variables
        self.lens1_pos = 0
        self.lens2_pos = 0
        self.current_frame = None
        self.snapshot_mode = False
        self.camera_connected = False

        self.initUI()
        self.initCamera()

    def change_focus(self, delta_mm):
        """Изменение фокуса с заданным шагом в мм"""
        try:
            current_mm = int(self.focus_input.text())
            new_mm = max(10, min(10000, current_mm + delta_mm))  # Ограничение 10мм-10м
            self.focus_input.setText(str(new_mm))
            self.update_focus()
        except ValueError:
            pass

    def update_focus(self):
        """Обновление фокуса камеры"""
        try:
            distance_mm = int(self.focus_input.text())
            if not (10 <= distance_mm <= 10000):
                raise ValueError("Диапазон фокуса: 10-10000 мм")
                
            # Обновляем текущие настройки
            self.current_settings['focus'] = distance_mm
            
            # Преобразование мм в lens-position (1/метры)
            lens_position = 1.0 / (distance_mm / 1000.0)
            
            if hasattr(self, 'camera_thread') and self.camera_connected:
                self.camera_thread.camera.set_controls({
                    "AfMode": controls.AfModeEnum.Manual,
                    "LensPosition": lens_position
                })
        except Exception as e:
            print(f"Ошибка фокусировки: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось установить фокус: {e}")

    def take_and_save_snapshot(self):
        """Take a high-quality snapshot with proper exposure handling"""
        if not self.camera_connected:
            QMessageBox.warning(self, "Error", "Camera not connected!")
            return

        try:
            os.makedirs("./results", exist_ok=True)
            exposure_time = float(self.exposure_input.text())  # in seconds
            
            # 1. Сохраняем текущие настройки камеры
            saved_settings = self.camera_thread.save_current_settings()
            
            # 2. Stop camera thread and wait for it to finish
            if hasattr(self.camera_thread, 'running'):
                self.camera_thread.running = False
                self.camera_thread.wait()
            
            # 3. Create a new camera instance for capture to avoid state conflicts
            capture_cam = Picamera2()
            
            # 4. Configure for high-quality capture
            config = capture_cam.create_still_configuration(
                main={"size": capture_cam.sensor_resolution, "format": "RGB888"},
                raw={},
                buffer_count=2
            )
            capture_cam.configure(config)
            
            # 5. Восстанавливаем основные настройки (кроме разрешения и формата)
            if saved_settings:
                # Исключаем настройки, которые не хотим переносить
                excluded = {'FrameSize', 'PixelFormat', 'ScalerCrop', 'SensorTimestamp'}
                restore_settings = {k: v for k, v in saved_settings.items() 
                                if k not in excluded}
                
                # Устанавливаем выдержку из UI, переопределяя сохраненное значение
                restore_settings['ExposureTime'] = int(exposure_time * 1000000)  # microseconds
                
                try:
                    capture_cam.set_controls(restore_settings)
                except Exception as e:
                    print(f"Couldn't restore some camera settings: {e}")
            
            # 6. Start capture camera
            capture_cam.start()
            time.sleep(1)  # Allow for settings to take effect
            
            # 7. Capture image
            timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
            rgb_filename = f"./results/{timestamp}.tiff"
            raw_filename = f"./results/{timestamp}.raw"
            
            request = capture_cam.capture_request()
            rgb_image = request.make_image("main")
            rgb_image.save(rgb_filename, quality=100)
            
            raw_data = request.make_array("raw")
            raw_data.tofile(raw_filename)
            request.release()
            
            # 8. Clean up capture camera
            capture_cam.stop()
            capture_cam.close()
            
            # 9. Restart preview thread
            if hasattr(self, 'camera_thread'):
                self.camera_thread.running = True
                self.camera_thread.start()
            
            QMessageBox.information(self, "Success", 
                                f"Images saved:\n"
                                f"RGB: {rgb_filename}\n"
                                f"RAW: {raw_filename}")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error details: {error_details}")
            
            QMessageBox.critical(self, "Error", f"Failed to save snapshot: {str(e)}")
            
            # Ensure preview is restarted in case of error
            if hasattr(self, 'camera_thread'):
                self.camera_thread.running = True
                self.camera_thread.start()


    def initUI(self):
        # Main style setup
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #aaa;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QPushButton {
                min-width: 80px;
                min-height: 30px;
                background-color: #e0e0e0;
                border: 1px solid #aaa;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QLabel {
                font-size: 13px;
            }
            QLineEdit {
                border: 1px solid #aaa;
                border-radius: 3px;
                padding: 3px;
            }
        """)

        # Create menu bar
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #e0e0e0;
                padding: 5px;
            }
            QMenuBar::item {
                padding: 5px 10px;
                background: transparent;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background: #c0c0c0;
            }
        """)

        # Instruction menu
        instruction_menu = menubar.addMenu("Инструкция")
        instruction_action = QAction("Показать инструкцию", self)
        instruction_action.triggered.connect(self.show_instruction)
        instruction_menu.addAction(instruction_action)

        # Settings menu
        settings_menu = menubar.addMenu("Настройки")
        settings_action = QAction("Открыть настройки камеры", self)
        settings_action.triggered.connect(self.show_settings_dialog)
        settings_menu.addAction(settings_action)

        # Main widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout (horizontal)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # Left part - video stream
        video_frame = QFrame()
        video_frame.setFrameShape(QFrame.StyledPanel)
        video_frame.setStyleSheet("background-color: black;")
        video_layout = QVBoxLayout(video_frame)
        video_layout.setContentsMargins(0, 0, 0, 0)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(740, 555)
        video_layout.addWidget(self.video_label)

        main_layout.addWidget(video_frame, stretch=3)

        # Right part - controls
        control_frame = QFrame()
        control_frame.setFrameShape(QFrame.StyledPanel)
        control_layout = QVBoxLayout(control_frame)
        control_layout.setContentsMargins(10, 10, 10, 10)
        control_layout.setSpacing(15)

        # Snapshot button
        self.snapshot_btn = QPushButton("Сделать снимок")
        self.snapshot_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                min-height: 40px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.snapshot_btn.clicked.connect(self.take_and_save_snapshot)  # Изменили обработчик
        control_layout.addWidget(self.snapshot_btn)

        # Lens control group
        lens_group = QGroupBox("Управление линзами")
        lens_layout = QHBoxLayout()
        lens_layout.setSpacing(15)

        # Lens 1
        lens1_group = QGroupBox("Линза 1")
        lens1_layout = QVBoxLayout()
        lens1_layout.setSpacing(8)

        self.lens1_pos_label = QLabel("Положение, мм")
        self.lens1_pos_label.setAlignment(Qt.AlignCenter)
        self.lens1_pos_input = QLineEdit("0")
        self.lens1_pos_input.setValidator(QIntValidator())
        self.lens1_pos_input.returnPressed.connect(self.update_lens1_pos)

        lens1_btn_layout = QHBoxLayout()
        lens1_btn_layout.setSpacing(5)
        self.lens1_backward_btn = QPushButton("← Назад")
        self.lens1_backward_btn.clicked.connect(lambda: self.change_lens_pos(1, -1))
        self.lens1_forward_btn = QPushButton("Вперед →")
        self.lens1_forward_btn.clicked.connect(lambda: self.change_lens_pos(1, 1))

        lens1_btn_layout.addWidget(self.lens1_backward_btn)
        lens1_btn_layout.addWidget(self.lens1_forward_btn)

        lens1_layout.addWidget(self.lens1_pos_label)
        lens1_layout.addWidget(self.lens1_pos_input)
        lens1_layout.addLayout(lens1_btn_layout)
        lens1_group.setLayout(lens1_layout)

        # Lens 2
        lens2_group = QGroupBox("Линза 2")
        lens2_layout = QVBoxLayout()
        lens2_layout.setSpacing(8)

        self.lens2_pos_label = QLabel("Положение, мм")
        self.lens2_pos_label.setAlignment(Qt.AlignCenter)
        self.lens2_pos_input = QLineEdit("0")
        self.lens2_pos_input.setValidator(QIntValidator())
        self.lens2_pos_input.returnPressed.connect(self.update_lens2_pos)

        lens2_btn_layout = QHBoxLayout()
        lens2_btn_layout.setSpacing(5)
        self.lens2_backward_btn = QPushButton("← Назад")
        self.lens2_backward_btn.clicked.connect(lambda: self.change_lens_pos(2, -1))
        self.lens2_forward_btn = QPushButton("Вперед →")
        self.lens2_forward_btn.clicked.connect(lambda: self.change_lens_pos(2, 1))

        lens2_btn_layout.addWidget(self.lens2_backward_btn)
        lens2_btn_layout.addWidget(self.lens2_forward_btn)

        lens2_layout.addWidget(self.lens2_pos_label)
        lens2_layout.addWidget(self.lens2_pos_input)
        lens2_layout.addLayout(lens2_btn_layout)
        lens2_group.setLayout(lens2_layout)

        lens_layout.addWidget(lens1_group)
        lens_layout.addWidget(lens2_group)
        lens_group.setLayout(lens_layout)
        control_layout.addWidget(lens_group)

        # Camera control group (объединенные фокус и выдержка)
        camera_group = QGroupBox("Камера")
        camera_layout = QHBoxLayout()
        camera_layout.setSpacing(15)

        # Focus control
        focus_group = QGroupBox("Фокус (10мм-10м)")
        focus_layout = QVBoxLayout()
        focus_layout.setSpacing(8)

        self.focus_input = QLineEdit("1000")  # Начальное значение 1 метр
        self.focus_input.setValidator(QIntValidator(10, 10000))  # Ограничение 10мм-10м
        self.focus_input.returnPressed.connect(self.update_focus)
        self.focus_input.setToolTip("Расстояние фокусировки в миллиметрах")

        focus_btn_layout = QHBoxLayout()
        focus_btn_layout.setSpacing(5)

        self.focus_decrease_btn = QPushButton("− Уменьшить")
        self.focus_decrease_btn.clicked.connect(lambda: self.change_focus(-50))  # Шаг 50мм
        self.focus_increase_btn = QPushButton("Увеличить +")
        self.focus_increase_btn.clicked.connect(lambda: self.change_focus(50))   # Шаг 50мм

        focus_btn_layout.addWidget(self.focus_decrease_btn)
        focus_btn_layout.addWidget(self.focus_increase_btn)

        focus_layout.addWidget(self.focus_input)
        focus_layout.addLayout(focus_btn_layout)
        focus_group.setLayout(focus_layout)

        # Exposure control
        exposure_group = QGroupBox("Выдержка, сек")
        exposure_layout = QVBoxLayout()
        exposure_layout.setSpacing(8)

        self.exposure_input = QLineEdit(str(self.current_settings['exposure']))
        self.exposure_input.setValidator(QDoubleValidator(0.1, 30.0, 1))
        self.exposure_input.returnPressed.connect(self.update_exposure)

        exposure_btn_layout = QHBoxLayout()
        exposure_btn_layout.setSpacing(5)
        self.exposure_decrease_btn = QPushButton("− Уменьшить")
        self.exposure_decrease_btn.clicked.connect(lambda: self.change_exposure(-0.5))
        self.exposure_increase_btn = QPushButton("Увеличить +")
        self.exposure_increase_btn.clicked.connect(lambda: self.change_exposure(0.5))

        exposure_btn_layout.addWidget(self.exposure_decrease_btn)
        exposure_btn_layout.addWidget(self.exposure_increase_btn)

        exposure_layout.addWidget(self.exposure_input)
        exposure_layout.addLayout(exposure_btn_layout)
        exposure_group.setLayout(exposure_layout)

        camera_layout.addWidget(focus_group)
        camera_layout.addWidget(exposure_group)
        camera_group.setLayout(camera_layout)
        control_layout.addWidget(camera_group)

        # Add stretch to align controls to top
        control_layout.addStretch()

        main_layout.addWidget(control_frame, stretch=1)

    def initCamera(self):
        self.camera_thread = CameraThread()
        self.camera_thread.change_pixmap.connect(self.set_image)
        self.camera_thread.camera_error.connect(self.handle_camera_error)
        self.camera_thread.settings_updated.connect(self.update_settings_from_camera)
        self.camera_thread.start()
        
        # Таймер для периодической синхронизации настроек с камерой
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.sync_camera_settings)
        self.sync_timer.start(1000)  # Синхронизация каждую секунду

    def sync_camera_settings(self):
        """Синхронизация текущих настроек с камерой"""
        if self.camera_connected:
            settings = {
                'exposure': self.current_settings['exposure']
            }
            self.camera_thread.update_settings(settings)

    def update_settings_from_camera(self, settings):
        """Обновление UI при изменении настроек камеры"""
        
        if 'exposure' in settings and settings['exposure'] != self.current_settings['exposure']:
            self.current_settings['exposure'] = settings['exposure']
            self.exposure_input.setText(str(settings['exposure']))

    def set_image(self, image):
        if not self.snapshot_mode:
            self.current_frame = image
            self.camera_connected = True
            pixmap = QPixmap.fromImage(image)
            self.video_label.setPixmap(pixmap.scaled(
                self.video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))

    def handle_camera_error(self):
        self.camera_connected = False
        if hasattr(self.camera_thread, 'no_camera_image'):
            pixmap = QPixmap.fromImage(self.camera_thread.no_camera_image)
            self.video_label.setPixmap(pixmap.scaled(
                self.video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
        else:
            self.video_label.setText("Камера не подключена")

    def resizeEvent(self, event):
        if self.current_frame:
            self.set_image(self.current_frame)
        super().resizeEvent(event)

    def take_snapshot(self):
        if not self.camera_connected:
            QMessageBox.warning(self, "Ошибка", "Камера не подключена!")
            return

        if self.current_frame is None:
            return

        self.snapshot_mode = True
        pixmap = QPixmap.fromImage(self.current_frame)
        self.video_label.setPixmap(pixmap.scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        ))

        # Return to video after exposure time
        QTimer.singleShot(int(self.current_settings['exposure'] * 1000), self.return_to_video)

    def return_to_video(self):
        self.snapshot_mode = False

    def change_exposure(self, delta):
        try:
            new_value = float(self.exposure_input.text()) + delta
            new_value = max(0.1, min(30.0, new_value))
            self.current_settings['exposure'] = round(new_value, 1)
            self.exposure_input.setText(str(self.current_settings['exposure']))
            self.sync_camera_settings()  # Немедленная синхронизация
        except ValueError:
            pass

    def update_exposure(self):
        try:
            value = float(self.exposure_input.text())
            self.current_settings['exposure'] = max(0.1, min(30.0, value))
            self.exposure_input.setText(str(round(self.current_settings['exposure'], 1)))
            self.sync_camera_settings()  # Немедленная синхронизация
        except ValueError:
            pass

    def change_lens_pos(self, lens_num, delta):
        if lens_num == 1:
            self.lens1_pos += delta
            self.lens1_pos_input.setText(str(self.lens1_pos))
        else:
            self.lens2_pos += delta
            self.lens2_pos_input.setText(str(self.lens2_pos))

    def update_lens1_pos(self):
        try:
            value = int(self.lens1_pos_input.text())
            self.lens1_pos = value
        except ValueError:
            pass

    def update_lens2_pos(self):
        try:
            value = int(self.lens2_pos_input.text())
            self.lens2_pos = value
        except ValueError:
            pass

    def show_instruction(self):
        msg = QMessageBox()
        msg.setWindowTitle("Инструкция")
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

    def show_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Настройки камеры")
        dialog.setFixedSize(400, 500)
        
        layout = QVBoxLayout()
        
        # Brightness
        brightness_group = QGroupBox("Яркость (0.0-1.0)")
        brightness_layout = QHBoxLayout()
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.setValue(int(self.current_settings['brightness'] * 100))
        brightness_layout.addWidget(self.brightness_slider)
        self.brightness_value = QLabel(str(self.current_settings['brightness']))
        brightness_layout.addWidget(self.brightness_value)
        brightness_group.setLayout(brightness_layout)
        
        # Contrast
        contrast_group = QGroupBox("Контраст (0.0-2.0)")
        contrast_layout = QHBoxLayout()
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setRange(0, 200)
        self.contrast_slider.setValue(int(self.current_settings['contrast'] * 100))
        contrast_layout.addWidget(self.contrast_slider)
        self.contrast_value = QLabel(str(self.current_settings['contrast']))
        contrast_layout.addWidget(self.contrast_value)
        contrast_group.setLayout(contrast_layout)
        
        # Saturation
        saturation_group = QGroupBox("Насыщенность (0.0-2.0)")
        saturation_layout = QHBoxLayout()
        self.saturation_slider = QSlider(Qt.Horizontal)
        self.saturation_slider.setRange(0, 200)
        self.saturation_slider.setValue(int(self.current_settings['saturation'] * 100))
        saturation_layout.addWidget(self.saturation_slider)
        self.saturation_value = QLabel(str(self.current_settings['saturation']))
        saturation_layout.addWidget(self.saturation_value)
        saturation_group.setLayout(saturation_layout)
        
        # Sharpness
        sharpness_group = QGroupBox("Резкость (0.0-2.0)")
        sharpness_layout = QHBoxLayout()
        self.sharpness_slider = QSlider(Qt.Horizontal)
        self.sharpness_slider.setRange(0, 200)
        self.sharpness_slider.setValue(int(self.current_settings['sharpness'] * 100))
        sharpness_layout.addWidget(self.sharpness_slider)
        self.sharpness_value = QLabel(str(self.current_settings['sharpness']))
        sharpness_layout.addWidget(self.sharpness_value)
        sharpness_group.setLayout(sharpness_layout)
        
        # AWB Mode
        awb_group = QGroupBox("Баланс белого")
        awb_layout = QVBoxLayout()
        self.awb_combo = QComboBox()
        self.awb_combo.addItems(['auto', 'incandescent', 'tungsten', 'fluorescent', 
                                'indoor', 'daylight', 'cloudy', 'custom'])
        self.awb_combo.setCurrentText(self.current_settings['awb_mode'])
        awb_layout.addWidget(self.awb_combo)
        awb_group.setLayout(awb_layout)
        
        # Exposure Mode
        exposure_group = QGroupBox("Режим экспозиции")
        exposure_layout = QVBoxLayout()
        self.exposure_combo = QComboBox()
        self.exposure_combo.addItems(['auto', 'normal', 'short', 'long', 'custom'])
        self.exposure_combo.setCurrentText(self.current_settings['exposure_mode'])
        exposure_layout.addWidget(self.exposure_combo)
        exposure_group.setLayout(exposure_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        apply_btn = QPushButton("Применить")
        apply_btn.clicked.connect(lambda: self.apply_camera_settings(dialog))
        reset_btn = QPushButton("Сбросить")
        reset_btn.clicked.connect(self.confirm_reset_settings)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(apply_btn)
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(cancel_btn)
        
        # Add all to main layout
        layout.addWidget(brightness_group)
        layout.addWidget(contrast_group)
        layout.addWidget(saturation_group)
        layout.addWidget(sharpness_group)
        layout.addWidget(awb_group)
        layout.addWidget(exposure_group)
        layout.addLayout(button_layout)
        
        # Connect slider signals
        self.brightness_slider.valueChanged.connect(
            lambda v: self.brightness_value.setText(str(v / 100)))
        self.contrast_slider.valueChanged.connect(
            lambda v: self.contrast_value.setText(str(v / 100)))
        self.saturation_slider.valueChanged.connect(
            lambda v: self.saturation_value.setText(str(v / 100)))
        self.sharpness_slider.valueChanged.connect(
            lambda v: self.sharpness_value.setText(str(v / 100)))
        
        dialog.setLayout(layout)
        dialog.exec_()

    def apply_camera_settings(self, dialog):
        self.current_settings.update({
            'brightness': float(self.brightness_value.text()),
            'contrast': float(self.contrast_value.text()),
            'saturation': float(self.saturation_value.text()),
            'sharpness': float(self.sharpness_value.text()),
            'awb_mode': self.awb_combo.currentText(),
            'exposure_mode': self.exposure_combo.currentText()
        })
        
        if self.camera_connected and hasattr(self.camera_thread, 'camera'):
            try:
                camera = self.camera_thread.camera
                camera.set_controls({
                    'AwbMode': self.get_awb_mode(self.current_settings['awb_mode']),
                    'AeExposureMode': self.get_exposure_mode(self.current_settings['exposure_mode']),
                    'Brightness': self.current_settings['brightness'],
                    'Contrast': self.current_settings['contrast'],
                    'Saturation': self.current_settings['saturation'],
                    'Sharpness': self.current_settings['sharpness']
                })
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось применить настройки: {e}")
        
        dialog.accept()

    def confirm_reset_settings(self):
        reply = QMessageBox.question(
            self, 'Подтверждение',
            'Вы уверены, что хотите сбросить настройки камеры к значениям по умолчанию?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.current_settings.update(self.default_settings)
            if self.camera_connected and hasattr(self.camera_thread, 'camera'):
                try:
                    camera = self.camera_thread.camera
                    camera.set_controls({
                        'AwbMode': self.get_awb_mode(self.default_settings['awb_mode']),
                        'AeExposureMode': self.get_exposure_mode(self.default_settings['exposure_mode']),
                        'Brightness': self.default_settings['brightness'],
                        'Contrast': self.default_settings['contrast'],
                        'Saturation': self.default_settings['saturation'],
                        'Sharpness': self.default_settings['sharpness']
                    })
                except Exception as e:
                    QMessageBox.warning(self, "Ошибка", f"Не удалось сбросить настройки: {e}")

    def get_awb_mode(self, mode_str):
        awb_modes = {
            'auto': controls.AwbModeEnum.Auto,
            'incandescent': controls.AwbModeEnum.Incandescent,
            'tungsten': controls.AwbModeEnum.Tungsten,
            'fluorescent': controls.AwbModeEnum.Fluorescent,
            'indoor': controls.AwbModeEnum.Indoor,
            'daylight': controls.AwbModeEnum.Daylight,
            'cloudy': controls.AwbModeEnum.Cloudy,
            'custom': controls.AwbModeEnum.Custom
        }
        return awb_modes.get(mode_str, controls.AwbModeEnum.Auto)

    def get_exposure_mode(self, mode_str):
        exposure_modes = {
            'auto': controls.AeExposureModeEnum.Normal,
            'normal': controls.AeExposureModeEnum.Normal,
            'short': controls.AeExposureModeEnum.Short,
            'long': controls.AeExposureModeEnum.Long,
            'custom': controls.AeExposureModeEnum.Custom
        }
        return exposure_modes.get(mode_str.lower(), controls.AeExposureModeEnum.Normal)

    def closeEvent(self, event):
        if hasattr(self, 'camera_thread'):
            self.camera_thread.stop()
        if hasattr(self, 'sync_timer'):
            self.sync_timer.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Set default font
    font = QFont()
    font.setPointSize(10)
    app.setFont(font)

    window = CameraApp()
    window.show()
    sys.exit(app.exec_())