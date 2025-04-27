# для объединения классов и функций в 1 модуль

from .main_window import CameraApp
from .dialogs import show_instruction_dialog, show_settings_dialog, apply_camera_settings, confirm_reset_settings
from .ui_setup import setup_styles, create_menu_bar, setup_video_panel, setup_control_panel, setup_snapshot_button, setup_lens_controls, setup_camera_controls, set_window_icon

__all__ = [
    'CameraApp',
    'show_instruction_dialog',
    'show_settings_dialog',
    'apply_camera_settings', 
    'confirm_reset_settings',
    'setup_styles', 
    'create_menu_bar', 
    'setup_video_panel', 
    'setup_control_panel', 
    'setup_snapshot_button', 
    'setup_lens_controls', 
    'setup_camera_controls', 
    'set_window_icon'
]