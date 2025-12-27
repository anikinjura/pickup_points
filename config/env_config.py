import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

def get_env_variable(var_name, default_value=None, cast_type=None):
    """
    Получает значение переменной окружения с возможностью приведения типа
    и возврата значения по умолчанию
    """
    value = os.environ.get(var_name, default_value)
    if value is None:
        return None
    
    if cast_type:
        try:
            if cast_type == bool:
                # Обработка булевых значений
                return str(value).lower() in ['true', '1', 'yes', 'on']
            return cast_type(value)
        except (ValueError, TypeError):
            return default_value
    return value