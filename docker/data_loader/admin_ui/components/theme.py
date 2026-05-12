# admin_ui/components/theme.py
"""Глобальные стили для тёмной темы."""

DARK_THEME_CSS = """
<style>
    /* 🔥 БАЗОВЫЕ НАСТРОЙКИ */
    html{{background:#1a1a1a}}
    body{{background:#1a1a1a!important;color:#fff!important}}

    /* 🔥 ЗАГОЛОВКИ — ЯВНЫЙ ЦВЕТ И ФОН */
    h1, h2, h3, h4, h5, h6{{color:#fff!important}}
    header, .card>header, article>header{{
        background:#2a2a2a!important;
        color:#fff!important;
        border-bottom:1px solid #444!important
    }}

    /* 🔥 ТЕКСТ ВНУТРИ ЗАГОЛОВКОВ */
    header strong, header b, header span, header small{{
        color:#fff!important
    }}

    /* 🔥 КАРТОЧКИ И СТАТЬИ */
    .card, article{{
        background:#252525!important;
        border:1px solid #444!important;
        color:#fff!important
    }}

    /* 🔥 ТАБЛИЦЫ */
    table{{background:#252525!important;color:#fff!important}}
    thead tr{{background:#2a2a2a!important}}
    th{{background:#2a2a2a!important;color:#fff!important;border-color:#444!important}}
    td{{background:#252525!important;color:#fff!important;border-color:#333!important}}

    /* 🔥 ФОРМЫ */
    input, select, textarea, button{{
        background:#333!important;
        color:#fff!important;
        border:1px solid #555!important
    }}
    input::placeholder{{color:#888!important}}

    /* 🔥 НАВБАРА И ССЫЛКИ */
    nav{{background:#252525!important;border:1px solid #444!important}}
    nav a{{color:#0d6efd!important}}
    nav a:hover{{color:#fff!important}}

    /* 🔥 КНОПКИ PICO */
    button.contrast, .contrast{{background:#0d6efd!important;color:#fff!important;border-color:#0d6efd!important}}
    button.secondary, .secondary{{background:#444!important;color:#ccc!important;border-color:#555!important}}

    /* 🔥 УТИЛИТЫ */
    .tfb{{transition:all 0.2s}}
    .big{{width:100%;padding:12px;font-size:1.1em;margin:15px 0}}
    a{{color:#0d6efd!important}}
    ::placeholder{{color:#888!important}}
</style>
"""

def render_head(title: str) -> str:
    """Генерирует <head> с тёмной темой."""
    return f"""
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1.0">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.dark.min.css">
        <title>{title}</title>
        {DARK_THEME_CSS}
    </head>
    """