# spectrometer_app/ui/ui_setup.py

import os
import sys
import subprocess
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QLineEdit, QGroupBox, QMenuBar, QAction, QFrame, QComboBox, QSlider,
                             QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QIcon

try:
    from utils.validators import ClampingIntValidator, ClampingDoubleValidator
    
except ImportError: # Fallback
    from spectrometer_app.utils.validators import ClampingIntValidator, ClampingDoubleValidator

def setup_styles(parent):
    """Настройка стилей интерфейса"""
    parent.setStyleSheet("""                         
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

def create_menu_bar(parent):
    """Создание меню бара"""

    menubar = parent.menuBar() # получение меню бара из главного окна

    # установка стиля
    menubar.setStyleSheet("""
        QMenuBar { 
            background-color: #f0f0f0; 
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

    """  Создание меню "Инструкция" """
    instruction_menu = menubar.addMenu("Инструкция")
    instruction_action = QAction("Показать инструкцию", parent)

     # Подключение к методу главного окна
    instruction_action.triggered.connect(parent.show_instruction_dialog)
    instruction_menu.addAction(instruction_action)

    """ Создание меню "Настройки" """
    settings_menu = menubar.addMenu("Настройки")
    settings_action = QAction("Открыть настройки камеры", parent)

    # Подключение к методу главного окна
    settings_action.triggered.connect(parent.show_settings_dialog) 
    settings_menu.addAction(settings_action)

def setup_video_panel(parent, main_layout):
    """Настройка панели видео"""
    
    video_frame = QFrame()                          # фрейм для видео
    video_frame.setFrameShape(QFrame.StyledPanel)
    video_frame.setStyleSheet("background-color: black;")   # фон - черный
    video_layout = QVBoxLayout(video_frame)         # вертикальный layout
    video_layout.setContentsMargins(0, 0, 0, 0)     # убираем отступы

    # Создание метки для отображения видео
    parent.video_label = QLabel()                   # сохраняем в родительском классе
    parent.video_label.setAlignment(Qt.AlignCenter) # выравнивание по центру
    parent.video_label.setMinimumSize(711, 530)     # минимальный размер
    video_layout.addWidget(parent.video_label)      # добавление в layout

    # Добавление в основной layout с коэффициентом растяжения
    main_layout.addWidget(video_frame, stretch=3)

def setup_control_panel(parent, main_layout):
    """Настройка панели управления"""
    control_frame = QFrame()                    # фрейм для панели управления
    control_frame.setFrameShape(QFrame.StyledPanel)
    control_layout = QVBoxLayout(control_frame) # вертикальный layout
    control_layout.setContentsMargins(10, 10, 10, 10)   # Отступы
    control_layout.setSpacing(15)               # расстояние между элементами

    # Настройка компонентов управления
    setup_snapshot_button(parent, control_layout)   # кнопка снимка 
    setup_lens_controls(parent, control_layout)     # управление линзами
    setup_camera_controls(parent, control_layout)   # управление камерой

    control_layout.addStretch() # растягивающийся элемент для выравнивания
    main_layout.addWidget(control_frame, stretch=1) # добавление в основной layout

def setup_snapshot_button(parent, layout):
    """Настройка кнопки снимка и кнопки открытия папки результатов"""

    # Создание кнопки снимка
    parent.snapshot_btn = QPushButton("Сделать снимок")
    
    # Настройка стиля
    parent.snapshot_btn.setStyleSheet("""
        QPushButton {
            background-color: #4CAF50; color: white;
            font-weight: bold; min-height: 40px; font-size: 14px;
        }
        QPushButton:hover { background-color: ##45a049; }
    """)

    # Подключение обработчика
    parent.snapshot_btn.clicked.connect(parent.take_and_save_snapshot) 

    # Добавление в layout
    layout.addWidget(parent.snapshot_btn)
    
    # Создание кнопки открытия папки результатов
    parent.open_results_btn = QPushButton("Результаты")
    parent.open_results_btn.setStyleSheet("""
        QPushButton {
            background-color: #e0e0e0; color: black;
            font-weight: bold; min-height: 40px; font-size: 14px;
        }
        QPushButton:hover { background-color: #d0d0d0; }
    """)
    
    # Подключение обработчика
    parent.open_results_btn.clicked.connect(parent.open_results_folder)
    
    # Добавление в layout
    layout.addWidget(parent.open_results_btn)

def setup_lens_controls(parent, layout):
    """Настройка управления позицией линз"""
    lens_group = QGroupBox("Управление линзами")    # Группа для линз
    lens_layout = QHBoxLayout()                     # Горизонтальный layout
    lens_layout.setSpacing(15)                      # Расстояние между элементами

    # Группа для линзы 1
    lens1_group = QGroupBox("Линза 1")
    lens1_layout = QVBoxLayout()        # Вертикальный layout
    lens1_layout.setSpacing(8)

    """ Элементы управления линзой 1 """ 
    parent.lens1_pos_label = QLabel("Положение, мм")    # Метка
    parent.lens1_pos_label.setAlignment(Qt.AlignCenter) # Выравнивание

    # Поле ввода
    parent.lens1_pos_input = QLineEdit(str(parent.current_settings['lens1_pos'])) 

    # Валидатор целых чисел
    parent.lens1_pos_input.setValidator(QIntValidator())  

    # Обработчик ввода    
    parent.lens1_pos_input.returnPressed.connect(parent.update_lens1_pos)
    

    """ Кнопки управления (тут все аналогичнее предыдущим комментариям файла) """
    lens1_btn_layout = QHBoxLayout()
    lens1_btn_layout.setSpacing(5)

    parent.lens1_backward_btn = QPushButton("← Назад") 
    parent.lens1_backward_btn.clicked.connect(lambda: parent.change_lens_pos(1, -1)) 
    parent.lens1_forward_btn = QPushButton("Вперед →") 
    parent.lens1_forward_btn.clicked.connect(lambda: parent.change_lens_pos(1, 1))
    
    # Добавление элементов в layout
    lens1_btn_layout.addWidget(parent.lens1_backward_btn)
    lens1_btn_layout.addWidget(parent.lens1_forward_btn)
    lens1_layout.addWidget(parent.lens1_pos_label)
    lens1_layout.addWidget(parent.lens1_pos_input)
    lens1_layout.addLayout(lens1_btn_layout)
    lens1_group.setLayout(lens1_layout)

    # Аналогичная настройка для линзы 2
    lens2_group = QGroupBox("Линза 2")
    lens2_layout = QVBoxLayout()
    lens2_layout.setSpacing(8)

    parent.lens2_pos_label = QLabel("Положение, мм")
    parent.lens2_pos_label.setAlignment(Qt.AlignCenter)
    parent.lens2_pos_input = QLineEdit(str(parent.current_settings['lens2_pos']))
    parent.lens2_pos_input.setValidator(QIntValidator())
    parent.lens2_pos_input.returnPressed.connect(parent.update_lens2_pos)

    lens2_btn_layout = QHBoxLayout()
    lens2_btn_layout.setSpacing(5)

    parent.lens2_backward_btn = QPushButton("← Назад")
    parent.lens2_backward_btn.clicked.connect(lambda: parent.change_lens_pos(2, -1))
    parent.lens2_forward_btn = QPushButton("Вперед →")
    parent.lens2_forward_btn.clicked.connect(lambda: parent.change_lens_pos(2, 1))

    lens2_btn_layout.addWidget(parent.lens2_backward_btn)
    lens2_btn_layout.addWidget(parent.lens2_forward_btn)
    lens2_layout.addWidget(parent.lens2_pos_label)
    lens2_layout.addWidget(parent.lens2_pos_input)
    lens2_layout.addLayout(lens2_btn_layout)
    lens2_group.setLayout(lens2_layout)

    lens_layout.addWidget(lens1_group)
    lens_layout.addWidget(lens2_group)
    lens_group.setLayout(lens_layout)
    layout.addWidget(lens_group)

def setup_camera_controls(parent, layout):
    """Настройка элементов управления камерой"""
    camera_group = QGroupBox("Камера")
    camera_layout = QHBoxLayout()
    camera_layout.setSpacing(15)

    # Группа управления фокусом
    focus_group = QGroupBox("Фокус, мм (10 - 10000)")
    focus_layout = QVBoxLayout()
    focus_layout.setSpacing(8)
    parent.focus_input = QLineEdit(str(parent.current_settings['focus']))
    parent.focus_input.setValidator(ClampingIntValidator(10, 10000))
    parent.focus_input.returnPressed.connect(parent.update_focus)

    # Кнопки управления фокусом
    focus_btn_layout = QHBoxLayout()
    focus_btn_layout.setSpacing(5)

    parent.focus_decrease_btn = QPushButton("− Уменьшить")
    parent.focus_decrease_btn.clicked.connect(lambda: parent.change_focus(-50))
    parent.focus_increase_btn = QPushButton("Увеличить +")
    parent.focus_increase_btn.clicked.connect(lambda: parent.change_focus(50))

    # Добавление элементов
    focus_btn_layout.addWidget(parent.focus_decrease_btn)
    focus_btn_layout.addWidget(parent.focus_increase_btn)
    focus_layout.addWidget(parent.focus_input)
    focus_layout.addLayout(focus_btn_layout)
    focus_group.setLayout(focus_layout)

    # Группа управления экспозицией (аналогично фокусу)
    exposure_group = QGroupBox("Выдержка, сек (0.1 - 30)")
    exposure_layout = QVBoxLayout()
    exposure_layout.setSpacing(8)

    parent.exposure_input = QLineEdit(f"{parent.current_settings['exposure']:.1f}")
    parent.exposure_input.setValidator(ClampingDoubleValidator(0.1, 30.0, 1))
    parent.exposure_input.returnPressed.connect(parent.update_exposure)

    exposure_btn_layout = QHBoxLayout()
    exposure_btn_layout.setSpacing(5)

    parent.exposure_decrease_btn = QPushButton("− Уменьшить")
    parent.exposure_decrease_btn.clicked.connect(lambda: parent.change_exposure(-0.5))
    parent.exposure_increase_btn = QPushButton("Увеличить +")
    parent.exposure_increase_btn.clicked.connect(lambda: parent.change_exposure(0.5))

    exposure_btn_layout.addWidget(parent.exposure_decrease_btn)
    exposure_btn_layout.addWidget(parent.exposure_increase_btn)
    exposure_layout.addWidget(parent.exposure_input)
    exposure_layout.addLayout(exposure_btn_layout)
    exposure_group.setLayout(exposure_layout)

    camera_layout.addWidget(focus_group)
    camera_layout.addWidget(exposure_group)
    camera_group.setLayout(camera_layout)
    layout.addWidget(camera_group)

def set_window_icon(parent):
    """Установка иконки окна"""

    # Путь к иконке
    icon_path = os.path.join(os.path.dirname(__file__), '../resources/icon.png')
    print(f"DEBUG: Attempting to load icon from: {icon_path}") # Добавлено для отладки

    # Установка иконки
    if os.path.exists(icon_path):
        print(f"DEBUG: Icon file found at: {icon_path}") # Добавлено для отладки
        icon = QIcon(icon_path)

        if icon.isNull():
            # QIcon не смог загрузить данные из файла
            print(f"ERROR: QIcon created from {icon_path} is null. Check file format/integrity.")
        else:
            # QIcon успешно создан, проверяем доступные размеры
            print(f"INFO: QIcon loaded successfully. Available sizes: {icon.availableSizes()}")
            parent.setWindowIcon(icon)
            print("DEBUG: Window icon set.") # Добавлено для отладки
            
    else:
        print(f"Warning: Icon file not found at {icon_path}")
