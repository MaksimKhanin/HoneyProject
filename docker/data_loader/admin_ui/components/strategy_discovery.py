# admin_ui/utils/strategy_discovery.py
"""
🔍 Полностью автоматическое обнаружение стратегий и их параметров.
Никаких ручных реестров — сканируем код, читаем атрибуты.
"""
import importlib
import pkgutil
import inspect
import sys
from pathlib import Path
from typing import Dict, Type, Any, Optional
from strategy.strategy_core import BaseStrategy


def discover_strategies(strategies_module: str = "strategy.strategies") -> Dict[str, Type[BaseStrategy]]:
    """
    Сканирует модуль стратегий и находит все публичные классы, наследующие BaseStrategy.

    :return: {"TrailingTrend": TrailingTrendStrategy, ...}
    """
    registry = {}

    try:
        strategies_pkg = importlib.import_module(strategies_module)
        pkg_path = Path(strategies_pkg.__path__[0])

        for _, name, is_pkg in pkgutil.iter_modules([str(pkg_path)]):
            if is_pkg or name.startswith('_'):
                continue
            try:
                module = importlib.import_module(f"{strategies_module}.{name}")
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                            isinstance(attr, type) and
                            issubclass(attr, BaseStrategy) and
                            attr is not BaseStrategy and
                            hasattr(attr, 'name') and
                            attr.name  # name не пустой
                    ):
                        registry[attr.name] = attr
            except Exception as e:
                print(f"⚠️ Не удалось загрузить стратегию из {name}: {e}", file=sys.stderr)
    except ImportError as e:
        print(f"⚠️ Не удалось импортировать модуль стратегий: {e}", file=sys.stderr)

    return registry


def render_param_field_custom(field_name: str, label: str, schema: Dict[str, Any], current_value: Any) -> str:
    """
    Генерирует HTML-поле с ЗАДАННЫМ именем (field_name).
    Нужно для изоляции параметров разных тикеров/таймфреймов.
    """
    ptype = schema.get("type", "string")
    default = schema.get("default")
    value = current_value if current_value is not None else default
    desc = schema.get("desc", "")

    # 🔹 Select
    if ptype == "select" and "options" in schema:
        options_html = "".join(
            f'<option value="{opt}" {"selected" if str(opt) == str(value) else ""}>{opt}</option>'
            for opt in schema["options"]
        )
        return f'''
        <div style="margin-bottom:8px;">
            <label style="font-size:0.85em;color:var(--text-secondary);">{label}</label>
            <select name="{field_name}" style="width:100%;padding:8px;background:var(--bg-input);color:var(--text-primary);border:1px solid var(--border-color);border-radius:4px;">
                {options_html}
            </select>
            {f'<small style="color:var(--text-secondary);font-size:0.8em;">{desc}</small>' if desc else ''}
        </div>
        '''

    # 🔹 Boolean
    if ptype == "bool":
        checked = "checked" if value in (True, "true", "True") else ""
        return f'''
        <div style="margin-bottom:8px;display:flex;align-items:center;gap:8px;">
            <input type="checkbox" name="{field_name}" value="true" {checked} id="{field_name}">
            <label for="{field_name}" style="font-size:0.9em;color:var(--text-primary);">{label}</label>
            {f'<small style="color:var(--text-secondary);font-size:0.8em;margin-left:auto;">{desc}</small>' if desc else ''}
        </div>
        '''

    # 🔹 Number
    if ptype in ("int", "float"):
        step = "1" if ptype == "int" else "0.01"
        min_val = schema.get("min", "" if ptype == "float" else 1)
        max_val = schema.get("max", "")
        val_str = str(value) if value is not None else ""
        return f'''
        <div style="margin-bottom:8px;">
            <label style="font-size:0.85em;color:var(--text-secondary);">{label}</label>
            <input type="number" name="{field_name}" value="{val_str}" step="{step}" min="{min_val}" max="{max_val}"
                   style="width:100%;padding:8px;background:var(--bg-input);color:var(--text-primary);border:1px solid var(--border-color);border-radius:4px;">
            {f'<small style="color:var(--text-secondary);font-size:0.8em;">{desc}</small>' if desc else ''}
        </div>
        '''

    # 🔹 String
    val_str = str(value) if value is not None else ""
    return f'''
    <div style="margin-bottom:8px;">
        <label style="font-size:0.85em;color:var(--text-secondary);">{label}</label>
        <input type="text" name="{field_name}" value="{val_str}" 
               style="width:100%;padding:8px;background:var(--bg-input);color:var(--text-primary);border:1px solid var(--border-color);border-radius:4px;">
        {f'<small style="color:var(--text-secondary);font-size:0.8em;">{desc}</small>' if desc else ''}
    </div>
    '''

def get_strategy_schema(strategy_cls: Type[BaseStrategy]) -> Dict[str, Dict[str, Any]]:
    """
    Извлекает схему параметров из стратегии.

    Приоритет:
    1. strategy_cls._params_schema (если объявлен)
    2. Инспекция __init__ (если _params_schema нет)
    3. Пустой dict (будет показано простое JSON-поле)
    """
    # 🔥 1. Явная схема (лучший вариант)
    if hasattr(strategy_cls, '_params_schema') and strategy_cls._params_schema:
        return strategy_cls._params_schema

    # 🔥 2. Автоматическая инспекция __init__ (фоллбэк)
    try:
        sig = inspect.signature(strategy_cls.__init__)
        schema = {}
        for param_name, param in sig.parameters.items():
            if param_name in ('self', 'params', 'direction', 'kwargs', 'args'):
                continue  # Пропускаем служебные

            # Пытаемся угадать тип из аннотаций или дефолта
            ptype = param.annotation if param.annotation != inspect.Parameter.empty else type(param.default)
            if ptype == inspect.Parameter.empty:
                ptype = str

            schema[param_name] = {
                "type": _python_type_to_ui_type(ptype),
                "default": param.default if param.default != inspect.Parameter.empty else None,
                "desc": f"Параметр '{param_name}' (авто-определено)",
            }
        return schema
    except Exception:
        pass

    # 🔥 3. Ничего не нашли — вернём пустую схему (будет JSON-поле)
    return {}


def _python_type_to_ui_type(py_type) -> str:
    """Конвертирует Python-тип в тип для UI."""
    if py_type in (int, 'int'):
        return "int"
    if py_type in (float, 'float'):
        return "float"
    if py_type in (bool, 'bool'):
        return "bool"
    if py_type in (str, 'str'):
        return "string"
    return "string"  # дефолт


def render_param_field(param_name: str, schema: Dict[str, Any], current_value: Any) -> str:
    """
    Генерирует HTML-поле для одного параметра на основе схемы.

    Поддерживает: int, float, bool, string, select.
    """
    ptype = schema.get("type", "string")
    default = schema.get("default")
    value = current_value if current_value is not None else default
    desc = schema.get("desc", "")

    # 🔹 Select (для direction и других перечислений)
    if ptype == "select" and "options" in schema:
        options_html = "".join(
            f'<option value="{opt}" {"selected" if opt == value else ""}>{opt}</option>'
            for opt in schema["options"]
        )
        return f'''
        <div style="margin-bottom:8px;">
            <label style="font-size:0.85em;color:var(--text-secondary);">{param_name}</label>
            <select name="param_{param_name}" style="width:100%;padding:8px;background:var(--bg-input);color:var(--text-primary);border:1px solid var(--border-color);border-radius:4px;">
                {options_html}
            </select>
            {f'<small style="color:var(--text-secondary);font-size:0.8em;">{desc}</small>' if desc else ''}
        </div>
        '''

    # 🔹 Boolean (checkbox)
    if ptype == "bool":
        checked = "checked" if value else ""
        return f'''
        <div style="margin-bottom:8px;display:flex;align-items:center;gap:8px;">
            <input type="checkbox" name="param_{param_name}" value="true" {checked} id="chk_{param_name}">
            <label for="chk_{param_name}" style="font-size:0.9em;color:var(--text-primary);">{param_name}</label>
            {f'<small style="color:var(--text-secondary);font-size:0.8em;margin-left:auto;">{desc}</small>' if desc else ''}
        </div>
        '''

    # 🔹 Number (int/float с min/max)
    if ptype in ("int", "float"):
        step = "1" if ptype == "int" else "0.01"
        min_val = schema.get("min", "" if ptype == "float" else 1)
        max_val = schema.get("max", "")
        return f'''
        <div style="margin-bottom:8px;">
            <label style="font-size:0.85em;color:var(--text-secondary);">{param_name}</label>
            <input type="number" name="param_{param_name}" value="{value if value is not None else ''}" 
                   step="{step}" min="{min_val}" max="{max_val}"
                   style="width:100%;padding:8px;background:var(--bg-input);color:var(--text-primary);border:1px solid var(--border-color);border-radius:4px;">
            {f'<small style="color:var(--text-secondary);font-size:0.8em;">{desc}</small>' if desc else ''}
        </div>
        '''

    # 🔹 String (текстовое поле)
    return f'''
    <div style="margin-bottom:8px;">
        <label style="font-size:0.85em;color:var(--text-secondary);">{param_name}</label>
        <input type="text" name="param_{param_name}" value="{value if value is not None else ''}" 
               style="width:100%;padding:8px;background:var(--bg-input);color:var(--text-primary);border:1px solid var(--border-color);border-radius:4px;">
        {f'<small style="color:var(--text-secondary);font-size:0.8em;">{desc}</small>' if desc else ''}
    </div>
    '''