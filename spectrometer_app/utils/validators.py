# spectrometer_app/utils/validators.py


from PyQt5.QtGui import QIntValidator, QDoubleValidator

# --- Кастомные валидаторы ---

class ClampingIntValidator(QIntValidator):
    """
    Целочисленный валидатор, который фиксирует значение в допустимых границах вместо простой инвалидации.
    """
    def fixup(self, input_str):
        try:
            value = int(input_str)

            if value < self.bottom():
                # Если меньше минимума - возвращаем минимальное значение
                return str(self.bottom())
            
            if value > self.top():
                 # Если больше максимума - возвращаем максимальное значение
                return str(self.top())
            
            """
            Если значение в допустимом диапазоне, но плохо отформатировано 
            (например, с ведущими нулями), возвращаем каноническое строковое 
            представление
            """
            return str(value)
        
        except ValueError:
            # Если ввод вообще не является целым числом - вернем минимум
            return str(self.bottom())

class ClampingDoubleValidator(QDoubleValidator):
    """Валидатор чисел с плавающей точкой"""

    # все аналогично
    def fixup(self, input_str):
        try:
            # Пытаемся интерпретировать с учетом локали
            value, ok = self.locale().toDouble(input_str)

            if not ok: # Если не удалось через локаль, то через прямое преобразование
                value = float(input_str)

            bottom = self.bottom()
            top = self.top()
            decimals = self.decimals()

            if value < bottom:
                return self.locale().toString(bottom, 'f', decimals)
            
            if value > top:
                return self.locale().toString(top, 'f', decimals)

            return self.locale().toString(value, 'f', decimals)

        except ValueError:
            return self.locale().toString(self.bottom(), 'f', self.decimals())