# admin_ui/components/helpers.py
"""Общие хелперы для UI."""

def fmt(val, pattern=".2f", default="N/A", prefix="", suffix=""):
    """Безопасное форматирование: число → строка, None → дефолт."""
    if val is None:
        return default
    formatted = f"{val:{pattern}}"
    return f"{prefix}{formatted}{suffix}"

def fmt_price(val, currency="₽"):
    """Форматирование цены."""
    return fmt(val, ",.2f", "—", suffix=f" {currency}")

def fmt_pct(val):
    """Форматирование процента."""
    return fmt(val, "+.2f", "—", suffix="%")