# core/metrics/registry.py
"""
Реестр метрик: регистрация, обнаружение, получение по имени.
Поддерживает авто-загрузку из модулей builtins/*.py
"""

import importlib
import pkgutil
from typing import Dict, Type, List
from pathlib import Path

from .base import BaseMetric

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


def get_metric(name: str) -> Type[BaseMetric]:
    """Получает класс метрики по имени."""
    if name not in METRIC_REGISTRY:
        raise KeyError(f"Метрика '{name}' не найдена. Доступные: {list(METRIC_REGISTRY.keys())}")
    return METRIC_REGISTRY[name]


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