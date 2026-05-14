# admin_ui/components/navbar.py
"""Общий навбар для всех страниц."""


def render_navbar(active_page: str) -> str:
    tabs = {
        "/": ("📥 Загрузка", "Настройки инструментов и таймфреймов"),
        "/strategies": ("🧠 Стратегии", "Привязка алгоритмов к данным"),
        "/portfolio": ("📊 Портфель", "Статистика и метрики позиций"),
        "/signals": ("📡 Сигналы", "Последние сигналы от стратегий"),
    }
    links = ""
    for path, (label, desc) in tabs.items():
        active_class = "contrast" if path == active_page else "secondary"
        links += f'<a href="{path}" class="outline {active_class}" style="margin-right:5px;">{label}</a> '

    return f'''
    <nav style="margin-bottom:15px;padding:10px;background:#252525;border-radius:8px;display:flex;align-items:center;justify-content:space-between;">
        <div>
            <strong style="font-size:1.1em;">🎛 Honey Loader</strong>
            <small style="color:#aaa;margin-left:10px;">{tabs[active_page][1]}</small>
        </div>
        <div>{links}</div>
    </nav>
    '''