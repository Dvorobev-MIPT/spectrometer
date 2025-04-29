"""
Spectrometer Application

Основной пакет для управления спектрометром на базе Raspberry Pi Camera.
"""

__version__ = "0.0.2"
__author__ = "Vorobev Dmitri Alexandrovich"
__email__ = "vorobev.da@phystech.edu"

# Реэкспорт основных классов для удобного импорта
from .core.camera_thread import CameraThread
from .ui.main_window import CameraApp

__all__ = [
    'CameraThread',
    'CameraApp',
]