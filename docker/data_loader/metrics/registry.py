# core/metrics/registry.py
"""
Реестр метрик: регистрация, обнаружение, получение по имени.
Поддерживает авто-загрузку из модулей builtins/*.py
Работает с параметризованными метриками (period, window).
"""

import importlib
import pkgutil
import re
from typing import Dict, Type, List, Optional, Any
from pathlib import Path

from .base import BaseMetric, PandasMetric

# Глобальный реестр: name -> класс метрики
METRIC_REGISTRY: Dict[str, Type[BaseMetric]] = {}


def register_metric(metric_class: Type[BaseMetric]):
    """Регистрирует класс метрики в реестре."""
    if not issubclass(metric_class, BaseMetric):
        raise TypeError(f"{metric_class} должен наследовать BaseMetric")

    name = getattr(metric_class, 'name', None)
    if not name:
        raise ValueError(f"Метрика {metric_class} должна иметь атрибут 'name'")

    METRIC_REGISTRY[name] = metric_class
    return metric_class  # Для использования как декоратор


def get_metric(name: str, period: Optional[int] = None, window: Optional[int] = None) -> BaseMetric:
    """
    Получает или создаёт экземпляр метрики по имени.
    
    :param name: имя метрики (например, "rsi_14" или "rsi_{period}")
    :param period: период для параметризованных метрик (опционально)
    :param window: окно для параметризованных метрик (опционально)
    :return: экземпляр метрики
    
    Примеры:
        get_metric("rsi_14")  # Вернёт RSI с period=14
        get_metric("rsi", period=21)  # Вернёт RSI с period=21
        get_metric("pullback", window=30)  # Вернёт Pullback с window=30
    """
    # Пытаемся найти точное совпадение имени
    if name in METRIC_REGISTRY:
        metric_class = METRIC_REGISTRY[name]
        # Если метрика параметризованная, создаём экземпляр с параметрами
        if issubclass(metric_class, PandasMetric):
            return metric_class(period=period, window=window)
        return metric_class()
    
    # Пытаемся найти шаблон с плейсхолдерами
    for template_name, metric_class in METRIC_REGISTRY.items():
        # Проверяем, содержит ли имя шаблона плейсхолдеры
        if '{period}' in template_name or '{window}' in template_name:
            # Создаём регулярное выражение из шаблона
            pattern = template_name.replace('{period}', r'(\d+)').replace('{window}', r'(\d+)')
            pattern = f"^{pattern}$"
            match = re.match(pattern, name)
            
            if match:
                groups = match.groups()
                # Извлекаем параметры из имени
                extracted_period = None
                extracted_window = None
                
                idx = 0
                if '{period}' in template_name:
                    extracted_period = int(groups[idx])
                    idx += 1
                if '{window}' in template_name:
                    extracted_window = int(groups[idx])
                
                # Переопределяем переданными параметрами, если они есть
                final_period = period if period is not None else extracted_period
                final_window = window if window is not None else extracted_window
                
                return metric_class(period=final_period, window=final_window)
    
    # Если не нашли, пробуем интерпретировать имя как параметризованное
    # Например, "rsi_14" -> ищем класс "rsi_{period}" и создаём с period=14
    parts = name.rsplit('_', 1)
    if len(parts) == 2 and parts[1].isdigit():
        base_name = parts[0]
        value = int(parts[1])
        
        # Ищем шаблон с {period} или {window}
        for template_name, metric_class in METRIC_REGISTRY.items():
            if '{period}' in template_name and template_name.startswith(base_name + '_'):
                return metric_class(period=value)
            if '{window}' in template_name and template_name.startswith(base_name + '_'):
                return metric_class(window=value)
    
    raise KeyError(f"Метрика '{name}' не найдена. Доступные: {list_metrics()}")


def list_metrics() -> List[str]:
    """Возвращает список зарегистрированных имён метрик."""
    return list(METRIC_REGISTRY.keys())


def auto_discover(package_name: str = "metrics.builtins"):
    """
    Авто-обнаружение метрик в указанном пакете.
    Импортирует все модули и регистрирует классы, наследующие BaseMetric.
    """
    try:
        package = importlib.import_module(package_name)
        package_path = Path(package.__path__[0])

        for module_info in pkgutil.iter_modules([str(package_path)]):
            module_name = f"{package_name}.{module_info.name}"
            try:
                module = importlib.import_module(module_name)
                # Ищем классы в модуле
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                            isinstance(attr, type)
                            and issubclass(attr, BaseMetric)
                            and attr != BaseMetric
                            and hasattr(attr, 'name')
                    ):
                        register_metric(attr)
            except Exception as e:
                print(f"⚠️ Не удалось загрузить модуль {module_name}: {e}")

    except ImportError as e:
        print(f"⚠️ Не удалось импортировать пакет {package_name}: {e}")


# Авто-регистрация при импорте модуля
auto_discover()