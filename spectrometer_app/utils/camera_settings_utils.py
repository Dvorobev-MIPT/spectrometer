# spectrometer_app/utils/camera_settings_utils.py

import traceback
from libcamera import controls

try:
    from utils.config import DEFAULT_SETTINGS

except ImportError: # Fallback for running script directly
    try:
        from spectrometer_app.utils.config import DEFAULT_SETTINGS

    except ImportError:
        # Резервные настройки, если конфиг не найден
        print("Warning: Could not import DEFAULT_SETTINGS from config. Using fallback.")
        DEFAULT_SETTINGS = {
            'brightness':    0.0, 
            'contrast':      1.0, 
            'saturation':    1.0, 
            'sharpness':     1.0,
            'awb_mode':      'auto', 
            'exposure_mode': 'auto', 
            'focus':         1000,
            'exposure':      3.0, 
            'lens1_pos':     0, 
            'lens2_pos':     0
        }


def get_awb_mode(mode_str):
    """Преобразует строковый режим баланса белого в enum-значение"""

    # Словарь соответствия строковых значений enum-ам
    awb_modes = {
        'auto':         controls.AwbModeEnum.Auto,
        'incandescent': controls.AwbModeEnum.Incandescent,
        'tungsten':     controls.AwbModeEnum.Tungsten,
        'fluorescent':  controls.AwbModeEnum.Fluorescent,
        'indoor':       controls.AwbModeEnum.Indoor,
        'daylight':     controls.AwbModeEnum.Daylight,
        'cloudy':       controls.AwbModeEnum.Cloudy,
        'custom':       controls.AwbModeEnum.Custom
    }
    # Обработка входного параметра
    try:
        mode_key = str(mode_str).strip().lower() # нормализация строки
    except AttributeError:
        mode_key = 'auto'                        # значение по умолчанию при ошибке
    return awb_modes.get(mode_key, controls.AwbModeEnum.Auto)


def get_exposure_mode(mode_str):
    """Преобразует строковый режим экспозиции в enum-значение"""

    exposure_modes = {
        'auto':     controls.AeExposureModeEnum.Normal,
        'normal':   controls.AeExposureModeEnum.Normal,
        'short':    controls.AeExposureModeEnum.Short,
        'long':     controls.AeExposureModeEnum.Long,
        'custom':   controls.AeExposureModeEnum.Custom
    }

    # Обработка входного параметра
    try:
        mode_key = str(mode_str).strip().lower() # Нормализация строки

    except AttributeError:
        mode_key = 'auto'                        # Значение по умолчанию при ошибке

    return exposure_modes.get(mode_key, controls.AeExposureModeEnum.Normal)


def restore_camera_settings_from_qsettings(camera, settings_manager):
    """Восстанавливает базовые настройки из QSettings"""

    # Проверка наличия камеры
    if camera is None: 
        return False
    
    print("Restoring camera settings from QSettings...")

    try:
        controls_to_set = {}    # словарь для настроек

        # Получение и установка баланса белого
        awb_mode = settings_manager.value('awb_mode', 
                                          DEFAULT_SETTINGS['awb_mode'])
        controls_to_set['AwbMode'] = get_awb_mode(awb_mode)

        # Получение и установка режима экспозиции
        exp_mode = settings_manager.value('exposure_mode', 
                                          DEFAULT_SETTINGS['exposure_mode'])
        controls_to_set['AeExposureMode'] = get_exposure_mode(exp_mode)

        # Установка других основных параметров изображения
        for param in ['Brightness', 
                      'Contrast', 
                      'Saturation', 
                      'Sharpness']:
            default_key = param.lower()      # Ключ для DEFAULT_SETTINGS
            value = settings_manager.value(default_key, 
                                           DEFAULT_SETTINGS[default_key], type=float)
            controls_to_set[param] = value

        camera.set_controls(controls_to_set) # Применение настроек

        print("Restored settings from QSettings:", controls_to_set)
        return True
    
    except Exception as e:
        print(f"Error restoring camera settings from QSettings: {e}")
        return False


def apply_full_ui_settings_to_camera(camera, ui_settings):
    """
    Применяет к камере полный набор настроек из словаря.
    Возвращает словарь, содержащий фактически примененные значения фокуса 
    и экспозиции, или не содержит их, если не удалось выполнить.    
    """

    if camera is None or not camera.started:
        print("Camera not ready for apply_full_ui_settings")
        return None
    try:
        controls_to_set = {}    # Настройки для камеры
        applied_state = {}      # Состояние после применения

        # Установка режимов
        awb_mode_enum = get_awb_mode(ui_settings.get('awb_mode', 
                                                     DEFAULT_SETTINGS['awb_mode']))
        exp_mode_enum = get_exposure_mode(ui_settings.get('exposure_mode', 
                                                          DEFAULT_SETTINGS['exposure_mode']))

        controls_to_set['AwbMode']        = awb_mode_enum
        controls_to_set['AeExposureMode'] = exp_mode_enum

        # Базовые настройки изображения
        for key in ['brightness', 'contrast', 'saturation', 'sharpness']:
            controls_to_set[key.capitalize()] = ui_settings.get(key,
                                                                DEFAULT_SETTINGS[key])

        # Настройка экспозиции (ручной/авто режим)
        exposure_sec = ui_settings.get('exposure', DEFAULT_SETTINGS['exposure'])
        is_manual_exposure = exp_mode_enum == controls.AeExposureModeEnum.Custom

        if is_manual_exposure:
            controls_to_set['AeEnable']     = False
            # Конвертация в микросекунды
            controls_to_set['ExposureTime'] = int(exposure_sec * 1000000)
            applied_state['exposure']       = exposure_sec
        else:
            controls_to_set['AeEnable']     = True
             

        # Настройка фокуса
        focus_mm      = ui_settings.get('focus', DEFAULT_SETTINGS['focus'])
        lens_position = 1.0 / (focus_mm / 1000.0)   # позиция линзы камеры

        controls_to_set['AfMode']       = controls.AfModeEnum.Manual
        controls_to_set['LensPosition'] = lens_position
        applied_state['focus']          = focus_mm

        print(f"Applying full settings to camera: {controls_to_set}")
        camera.set_controls(controls_to_set) # применение всех настроек
        return applied_state                 # возврат примененных значений

    except Exception as e:
        print(f"Error applying full UI settings to camera: {e}")
        traceback.print_exc()
        return None


def set_camera_focus(camera, distance_mm):
    """Устанавливает ручной фокус камеры на указанное расстояние"""
    if camera is None: 
        return False
    try:
        lens_position = 1.0 / (distance_mm / 1000.0) # позиция линзы камеры
        
        camera.set_controls({"AfMode": controls.AfModeEnum.Manual,
                             "LensPosition": lens_position})
        print(f"Set camera focus to {distance_mm}mm (LensPosition: {lens_position})")
        return True
    except Exception as e:
        print(f"Focus error: {e}")
        return False


def update_specific_camera_settings(camera, settings_dict):
    """
    Обновляет конкретные настройки камеры из словаря
    Возвращает словарь, содержащий фактически примененные значения фокуса 
    и экспозиции, или не содержит их, если не удалось выполнить. 
    """

    if camera is None or not camera.started: 
        return None
    try:
        controls_to_set = {}   # настройки для обновления
        applied_state   = {}   # обновленные настройки
        ae_enabled      = None # флак автоматической экспозиции

        # Обновление фокуса
        if 'focus' in settings_dict:
            focus_mm = settings_dict['focus']
            lens_position = 1.0 / (focus_mm / 1000.0)
            controls_to_set.update({"AfMode": controls.AfModeEnum.Manual, "LensPosition": lens_position})
            applied_state['focus'] = focus_mm

        # Обновление экспозиции
        if 'exposure' in settings_dict:
            exposure_sec = settings_dict['exposure']
            controls_to_set['ExposureTime'] = int(exposure_sec * 1000000)
            ae_enabled = False  # Ручной режим
            applied_state['exposure'] = exposure_sec

        # Обновление ae
        if ae_enabled is not None:
            controls_to_set['AeEnable'] = ae_enabled

        if controls_to_set:
            print(f"Updating specific camera settings: {controls_to_set}")
            camera.set_controls(controls_to_set)
            return applied_state    # вовзрат изменений
        return None                 # нет изменений
    
    except Exception as e:
        print(f"Failed to update specific camera settings: {e}")
        return None


def save_camera_metadata(camera, thread_current_settings):
    """Сохраняет метаданные камеры с текущими настройками фокуса/экспозиции"""
    if camera is None: 
        return {}
    
    try:
        metadata = camera.capture_metadata()    # Получение метаданных
        controls_dict = metadata.get("Controls", {})
        saved_settings = controls_dict.copy()

        # Сохранение актуальных значений фокуса и экспозиции
        saved_settings['ExposureTime'] = int(thread_current_settings['exposure'] * 1000000)
        saved_settings['LensPosition'] = 1.0 / (thread_current_settings['focus'] / 1000.0)

        print("Saved camera metadata merged with current state.")
        return saved_settings
    
    except Exception as e:
        print(f"Error saving camera metadata: {e}")
        return {}


def restore_last_camera_settings(camera, last_settings_dict):
    """Восстанавливает настройки из сохраненного словаря (исключая некоторые параметры)"""

    if camera is None or not last_settings_dict: 
        return False
    
    try:
        # Параметры, которые не нужно восстанавливать
        excluded = {'FrameSize', 
                    'PixelFormat', 
                    'ScalerCrop', 
                    'SensorTimestamp'}

        # Фильтрация параметров
        controls_to_set = {k: v for k, v in last_settings_dict.items() if k not in excluded}

        if controls_to_set:
            print(f"Restoring last camera settings: {controls_to_set}")
            camera.set_controls(controls_to_set)
            return True 
        
        return False  # Нет параметров для восстановления
    except Exception as e:
        print(f"Error restoring last camera settings: {e}")
        return False
