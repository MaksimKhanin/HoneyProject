# admin_ui.py
import os, yaml, traceback, math
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Depends, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
from config_manager import get_config_manager
from logger import setup_logger
from strategies import STRATEGY_REGISTRY

# === Конфигурация ===
CONFIG_PATH = os.getenv("CONFIG_PATH", "app/config.yaml")
CONFIG_MNG = get_config_manager(CONFIG_PATH)
CONFIG = CONFIG_MNG.get_config()

ADMIN_USER = os.getenv("UI_USER", "admin")
ADMIN_PASSWORD = os.getenv("UI_PASS", "admin")

logger = setup_logger(
    name="AdminUI",
    log_file=CONFIG['settings']['log_file'],
    level=CONFIG['settings']['log_level']
)

AVAILABLE_TIMEFRAMES = ["1m", "5m", "15m", "1h", "1d"]
TF_DEFAULTS = {
    "1m": {"history_depth_days": 7, "update_interval_minutes": 5},
    "5m": {"history_depth_days": 30, "update_interval_minutes": 15},
    "15m": {"history_depth_days": 60, "update_interval_minutes": 30},
    "1h": {"history_depth_days": 180, "update_interval_minutes": 60},
    "1d": {"history_depth_days": 365, "update_interval_minutes": 1440},
}

app = FastAPI()
security = HTTPBasic()


# === Auth ===
def check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != ADMIN_USER or credentials.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Access denied")
    return credentials.username


# === Конфиг ===
def load_config():
    return CONFIG_MNG.get_config() or {"instruments": []}


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return True


def get_tf_config(inst, tf_name):
    for tf in inst.get("timeframes", []):
        if tf.get("timeframe") == tf_name:
            return tf
    return None


# === Навбар (общий для всех страниц) ===
def render_navbar(active_page: str) -> str:
    tabs = {
        "/": ("📥 Загрузка", "Настройки инструментов и таймфреймов"),
        "/strategies": ("🧠 Стратегии", "Привязка алгоритмов к данным"),
        "/portfolio": ("📊 Портфель", "Статистика и метрики позиций"),
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


# === Страница 1: Настройки загрузки ===
@app.get("/", response_class=HTMLResponse)
async def page_loader(user: str = Depends(check_auth)):
    cfg = load_config()
    instruments = cfg.get("instruments", [])

    instruments_html = ""
    for idx, inst in enumerate(instruments):
        ticker = inst.get("ticker", "UNKNOWN")
        inst_enabled = inst.get("enabled", True)

        tf_buttons = ""
        for tf_name in AVAILABLE_TIMEFRAMES:
            tf_cfg = get_tf_config(inst, tf_name)
            is_enabled = tf_cfg.get("enabled", False) if tf_cfg else False

            settings_block = ""
            if is_enabled and tf_cfg:
                hist_val = tf_cfg.get('history_depth_days', TF_DEFAULTS[tf_name]['history_depth_days'])
                int_val = tf_cfg.get('update_interval_minutes', TF_DEFAULTS[tf_name]['update_interval_minutes'])

                settings_block = f'''
                <div id="st_{idx}_{tf_name}" style="margin:6px 0;padding:6px;background:#2a2a2a;border-radius:4px;display:block;font-size:0.85em;border-top:1px solid #444;">
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;">
                        <label>📅<input type="number" name="h_{idx}_{tf_name}" value="{hist_val}" min="1" max="3650" style="width:100%;padding:3px;"></label>
                        <label>🔄<input type="number" name="i_{idx}_{tf_name}" value="{int_val}" min="1" max="1440" style="width:100%;padding:3px;"></label>
                    </div>
                </div>
                '''

            btn_class = "contrast" if is_enabled else "secondary"
            checked_str = "checked" if is_enabled else ""

            tf_buttons += f'''
            <div style="text-align:center;margin:3px 0;">
                <input type="checkbox" id="cb_{idx}_{tf_name}" name="e_{idx}_{tf_name}" style="display:none;" {checked_str}>
                <span class="tfb {btn_class}" style="display:inline-block;padding:5px 8px;border-radius:4px;font-size:0.8em;cursor:pointer;width:100%;box-sizing:border-box;"
                      onclick="toggleTF(event, '{idx}_{tf_name}')">{tf_name}</span>
                {settings_block}
            </div>
            '''

        checked_main = "checked" if inst_enabled else ""
        instruments_html += f'''
        <article class="card" style="margin-bottom:10px;background:#252525;border:1px solid #444;">
            <header style="display:flex;justify-content:space-between;align-items:center;padding:10px;cursor:pointer;" onclick="toggleCard(this)">
                <strong style="font-size:1.1em;">{ticker}</strong>
                <label style="margin:0;"><input type="checkbox" name="ie_{idx}" role="switch" {checked_main}></label>
            </header>
            <div class="cb" style="padding:0 10px 10px;">
                <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:3px;margin:8px 0;">
                    {tf_buttons}
                </div>
            </div>
        </article>
        '''

    js_code = """
    <script>
        function toggleTF(event, id) {
            event.stopPropagation(); 
            const checkbox = document.getElementById('cb_' + id);
            checkbox.checked = !checkbox.checked;
            const span = event.currentTarget;
            span.classList.toggle('contrast', checkbox.checked);
            span.classList.toggle('secondary', !checkbox.checked);
            const settings = document.getElementById('st_' + id);
            if (settings) settings.style.display = checkbox.checked ? 'block' : 'none';
        }
        function toggleCard(header) {
            const body = header.parentElement.querySelector('.cb');
            body.style.display = body.style.display === 'none' ? 'block' : 'none';
        }
        document.addEventListener('DOMContentLoaded', () => {
            document.querySelectorAll('[id^="st_"]').forEach(el => {
                const id = el.id.replace('st_', '');
                const cb = document.getElementById('cb_' + id);
                if (cb && !cb.checked) el.style.display = 'none';
            });
        });
    </script>
    """

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css">
    <title>📥 Настройки загрузки | Honey Loader</title>
    <style>
        body{{background:#1a1a1a;color:#fff;padding:8px;font-family:system-ui}}
        .card{{margin-bottom:10px}}
        .tfb{{transition:all 0.2s}}
        .tfb.contrast{{background:#0d6efd;color:#fff;border:1px solid #0d6efd}}
        .tfb.secondary{{background:#444;color:#ccc;border:1px solid #555}}
        .big{{width:100%;padding:12px;font-size:1.1em;margin:15px 0}}
        input[type=number]{{background:#333;border:1px solid #555;color:#fff;padding:4px;border-radius:3px;}}
    </style>
</head>
<body>
    <main class="container">
        {render_navbar("/")}
        <form action="/save" method="post" id="mainForm">
            {instruments_html}
            <button type="submit" class="big contrast">💾 Сохранить настройки</button>
        </form>
        <article class="card" style="background:#252525;border:1px dashed #666;margin-top:15px;">
            <header><strong>➕ Добавить инструмент</strong></header>
            <form action="/add" method="post" style="display:grid;gap:8px;">
                <input type="text" name="t" placeholder="Тикер (например, SBER)" required style="padding:8px;">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                    <select name="tf" style="padding:8px;">
                        <option value="1d">1d</option><option value="1h">1h</option>
                        <option value="5m">5m</option><option value="1m">1m</option>
                    </select>
                    <button type="submit" class="contrast" style="padding:8px;">OK</button>
                </div>
            </form>
        </article>
    </main>
    {js_code}
</body>
</html>"""
    return html


# === Страница 2: Стратегии ===
@app.get("/strategies", response_class=HTMLResponse)
async def page_strategies(user: str = Depends(check_auth)):
    cfg = load_config()
    instruments = cfg.get("instruments", [])

    rows_html = ""
    for idx, inst in enumerate(instruments):
        ticker = inst.get("ticker", "UNKNOWN")
        for tf_name in AVAILABLE_TIMEFRAMES:
            tf_cfg = get_tf_config(inst, tf_name)
            if not tf_cfg or not tf_cfg.get("enabled", False):
                continue  # показываем только активные таймфреймы

            current_strategy = tf_cfg.get("strategy", "none")

            # Генерация опций стратегий
            strategy_options = ""
            for s_id, s_name in STRATEGY_REGISTRY.items():
                selected = "selected" if s_id == current_strategy else ""
                strategy_options += f'<option value="{s_id}" {selected}>{s_name}</option>'

            # Окно стратегии (опционально)
            window_val = tf_cfg.get("strategy_window", "")

            rows_html += f'''
            <tr style="border-bottom:1px solid #333;">
                <td style="padding:8px;"><strong>{ticker}</strong></td>
                <td style="padding:8px;text-align:center;"><code>{tf_name}</code></td>
                <td style="padding:8px;">
                    <select name="strat_{idx}_{tf_name}" style="width:100%;padding:5px;background:#333;color:#fff;border:1px solid #555;border-radius:3px;">
                        {strategy_options}
                    </select>
                </td>
                <td style="padding:8px;">
                    <input type="number" name="win_{idx}_{tf_name}" value="{window_val}" placeholder="авто" 
                           min="5" max="500" style="width:80px;padding:4px;background:#333;border:1px solid #555;color:#fff;border-radius:3px;">
                </td>
            </tr>
            '''

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css">
    <title>🧠 Стратегии | Honey Loader</title>
    <style>
        body{{background:#1a1a1a;color:#fff;padding:8px;font-family:system-ui}}
        table{{width:100%;border-collapse:collapse}}
        th{{text-align:left;padding:10px;background:#252525;border-bottom:2px solid #444}}
        td{{padding:8px;border-bottom:1px solid #333}}
        select,input{{background:#333;border:1px solid #555;color:#fff;padding:4px;border-radius:3px;}}
        .big{{width:100%;padding:12px;font-size:1.1em;margin:15px 0}}
    </style>
</head>
<body>
    <main class="container">
        {render_navbar("/strategies")}

        <article class="card" style="background:#252525;border:1px solid #444;">
            <header><strong>🎯 Привязка стратегий</strong></header>
            <form action="/save_strategies" method="post">
                <table>
                    <thead>
                        <tr>
                            <th>Тикер</th>
                            <th>Таймфрейм</th>
                            <th>Стратегия</th>
                            <th>Окно (свечи)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html if rows_html else '<tr><td colspan="4" style="text-align:center;color:#777;">Нет активных таймфреймов</td></tr>'}
                    </tbody>
                </table>
                <button type="submit" class="big contrast" style="margin-top:15px;">💾 Сохранить стратегии</button>
            </form>
        </article>

        <article class="card" style="background:#252525;border:1px dashed #666;margin-top:15px;">
            <header><strong>ℹ️ Справка</strong></header>
            <ul style="font-size:0.9em;color:#ccc;">
                <li><code>Окно</code> — сколько последних свечей использовать для расчёта (оставь пустым для авто)</li>
                <li>Стратегии запускаются только на <strong>активных</strong> таймфреймах</li>
                <li>Сигналы пишутся в таблицу <code>signals</code> и дублируются в Телеграм</li>
            </ul>
        </article>
    </main>
</body>
</html>"""
    return html


# === Страница 3: Портфель (статистика) ===
@app.get("/portfolio", response_class=HTMLResponse)
async def page_portfolio(user: str = Depends(check_auth)):
    # 🔥 Здесь мы читаем из БД статистику
    # Для примера — заглушка, потом подключим db_manager

    # Пример данных (в реальности — запрос к БД)
    portfolio_data = [
        {"ticker": "GAZP", "tf": "1h", "strategy": "rsi_oversold", "last_price": 152.34, "signals_24h": 3,
         "last_signal": "BUY", "last_signal_time": "2024-03-22 14:00"},
        {"ticker": "VTBR", "tf": "1d", "strategy": "sma_cross", "last_price": 0.089, "signals_24h": 0,
         "last_signal": "HOLD", "last_signal_time": "2024-03-20 00:00"},
    ]

    rows_html = ""
    for row in portfolio_data:
        signal_color = {"BUY": "#0f0", "SELL": "#f44", "HOLD": "#aaa"}.get(row["last_signal"], "#fff")
        rows_html += f'''
        <tr style="border-bottom:1px solid #333;">
            <td style="padding:8px;"><strong>{row["ticker"]}</strong> <small style="color:#777">({row["tf"]})</small></td>
            <td style="padding:8px;"><code>{row["strategy"]}</code></td>
            <td style="padding:8px;text-align:right;">{row["last_price"]:,.2f}</td>
            <td style="padding:8px;text-align:center;">{row["signals_24h"]}</td>
            <td style="padding:8px;text-align:center;"><span style="color:{signal_color};font-weight:bold;">{row["last_signal"]}</span></td>
            <td style="padding:8px;font-size:0.85em;color:#aaa;">{row["last_signal_time"]}</td>
        </tr>
        '''

    # 🔥 Простые метрики (чистый Python, без pandas)
    def calc_basic_stats(prices: list) -> dict:
        if not prices:
            return {"avg": None, "std": None, "min": None, "max": None, "sharpe_approx": None}
        n = len(prices)
        avg = sum(prices) / n
        variance = sum((x - avg) ** 2 for x in prices) / n if n > 1 else 0
        std = math.sqrt(variance)
        # Упрощённый Sharpe: (средняя доходность) / волатильность
        if n >= 2 and std > 0:
            returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, n) if prices[i - 1] != 0]
            avg_ret = sum(returns) / len(returns) if returns else 0
            sharpe = avg_ret / std * math.sqrt(252)  # годовая оценка
        else:
            sharpe = None
        return {
            "avg": avg, "std": std, "min": min(prices), "max": max(prices),
            "sharpe_approx": sharpe
        }

        # Пример расчёта для одного инструмента (в реальности — цикл по всем позициям)

    sample_prices = [150.1, 151.2, 150.8, 152.0, 152.34]  # заглушка
    stats = calc_basic_stats(sample_prices)

    # 🔥 Хелпер для безопасного форматирования
    def fmt(val, pattern=".2f", default="N/A"):
        return f"{val:{pattern}}" if val is not None else default

    metrics_html = f'''
       <article class="card" style="background:#252525;border:1px solid #444;margin-bottom:15px;">
           <header><strong>📈 Быстрые метрики (пример: GAZP)</strong></header>
           <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:10px;">
               <div style="background:#2a2a2a;padding:10px;border-radius:6px;text-align:center;">
                   <div style="color:#aaa;font-size:0.85em;">Средняя</div>
                   <div style="font-size:1.2em;font-weight:bold;">{fmt(stats["avg"])}</div>
               </div>
               <div style="background:#2a2a2a;padding:10px;border-radius:6px;text-align:center;">
                   <div style="color:#aaa;font-size:0.85em;">Волатильность (σ)</div>
                   <div style="font-size:1.2em;font-weight:bold;">{fmt(stats["std"], ".3f")}</div>
               </div>
               <div style="background:#2a2a2a;padding:10px;border-radius:6px;text-align:center;">
                   <div style="color:#aaa;font-size:0.85em;">Диапазон</div>
                   <div style="font-size:1.2em;font-weight:bold;">
                       {fmt(stats["min"])} – {fmt(stats["max"])}
                   </div>
               </div>
               <div style="background:#2a2a2a;padding:10px;border-radius:6px;text-align:center;">
                   <div style="color:#aaa;font-size:0.85em;">Sharpe (approx)</div>
                   <div style="font-size:1.2em;font-weight:bold;color:{'#0f0' if (stats["sharpe_approx"] or 0) > 0 else '#f44'};">
                       {fmt(stats["sharpe_approx"], "+.2f")}</div>
               </div>
           </div>
       </article>
       '''

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css">
    <title>📊 Портфель | Honey Loader</title>
    <style>
        body{{background:#1a1a1a;color:#fff;padding:8px;font-family:system-ui}}
        table{{width:100%;border-collapse:collapse}}
        th{{text-align:left;padding:10px;background:#252525;border-bottom:2px solid #444}}
        td{{padding:8px;border-bottom:1px solid #333}}
        .card{{margin-bottom:10px}}
        .refresh-btn{{background:#0d6efd;color:#fff;border:none;padding:8px 16px;border-radius:4px;cursor:pointer;font-size:0.9em;}}
        .refresh-btn:hover{{background:#0b5ed7}}
    </style>
    <script>
        // Авто-обновление каждые 60 сек
        setInterval(() => location.reload(), 60000);
    </script>
</head>
<body>
    <main class="container">
        {render_navbar("/portfolio")}

        {metrics_html}

        <article class="card" style="background:#252525;border:1px solid #444;">
            <header style="display:flex;justify-content:space-between;align-items:center;">
                <strong>🎯 Активные инструменты</strong>
                <button class="refresh-btn" onclick="location.reload()">🔄 Обновить</button>
            </header>
            <table>
                <thead>
                    <tr>
                        <th>Инструмент</th>
                        <th>Стратегия</th>
                        <th>Цена</th>
                        <th>Сигналы (24ч)</th>
                        <th>Последний сигнал</th>
                        <th>Время</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html if rows_html else '<tr><td colspan="6" style="text-align:center;color:#777;">Нет данных</td></tr>'}
                </tbody>
            </table>
        </article>

        <article class="card" style="background:#252525;border:1px dashed #666;">
            <header><strong>ℹ️ Пояснения к метрикам</strong></header>
            <ul style="font-size:0.9em;color:#ccc;">
                <li><strong>Sharpe (approx)</strong> — упрощённая оценка риск/доходность. >1 = хорошо, >2 = отлично</li>
                <li><strong>Волатильность (σ)</strong> — насколько цена "скачет". Чем больше, тем выше риск</li>
                <li>Данные обновляются автоматически каждые 60 секунд</li>
                <li>Для расчётов используются только свечи из БД (никакого pandas!)</li>
            </ul>
        </article>
    </main>
</body>
</html>"""
    return html


# === Handlers ===
@app.post("/save")
async def save_loader_settings(request: Request, user: str = Depends(check_auth)):
    logger.info("=== 🚨 SAVE LOADER SETTINGS ===")
    try:
        form = await request.form()
        cfg = load_config()
        instruments = cfg.get("instruments", [])
        changes = False

        for idx in range(len(instruments)):
            inst = instruments[idx]
            ticker = inst.get("ticker")

            # Главный enabled
            ie_key = f"ie_{idx}"
            ie_val = ie_key in form
            if inst.get("enabled", True) != ie_val:
                inst["enabled"] = ie_val
                changes = True

            for tf in AVAILABLE_TIMEFRAMES:
                key = f"e_{idx}_{tf}"
                is_on = key in form

                if is_on:
                    h = form.get(f"h_{idx}_{tf}")
                    i_val = form.get(f"i_{idx}_{tf}")
                    new_hist = int(h) if h and h.isdigit() else TF_DEFAULTS[tf]["history_depth_days"]
                    new_int = int(i_val) if i_val and i_val.isdigit() else TF_DEFAULTS[tf]["update_interval_minutes"]

                    existing = get_tf_config(inst, tf)
                    if existing:
                        if existing.get("history_depth_days") != new_hist or existing.get(
                                "update_interval_minutes") != new_int:
                            changes = True
                        existing.update({
                            "enabled": True,
                            "history_depth_days": new_hist,
                            "update_interval_minutes": new_int
                        })
                    else:
                        inst.setdefault("timeframes", []).append({
                            "timeframe": tf, "enabled": True,
                            "history_depth_days": new_hist,
                            "update_interval_minutes": new_int,
                            "strategy": "none"
                        })
                        changes = True
                else:
                    for tcfg in inst.get("timeframes", []):
                        if tcfg.get("timeframe") == tf and tcfg.get("enabled"):
                            tcfg["enabled"] = False
                            changes = True
                            break

            # Авто-удаление
            enabled_tfs = [tf for tf in inst.get("timeframes", []) if tf.get("enabled", False)]
            if len(enabled_tfs) == 0 and inst.get("timeframes"):
                inst["_del"] = True
                changes = True

        # Физическое удаление
        before = len(instruments)
        instruments = [i for i in instruments if not i.get("_del")]
        if len(instruments) < before:
            changes = True

        cfg["instruments"] = instruments

        if changes and save_config(cfg):
            return HTMLResponse(content="<script>alert('✅ Настройки загрузки сохранены!');location.href='/';</script>")
        return HTMLResponse(content="<script>location.href='/';</script>")

    except Exception as e:
        logger.error(f"💥 CRASH: {e}\n{traceback.format_exc()}")
        return HTMLResponse(content=f"<script>alert('💥 {e}');location.href='/';</script>", status_code=500)


@app.post("/save_strategies")
async def save_strategies(request: Request, user: str = Depends(check_auth)):
    logger.info("=== 🚨 SAVE STRATEGIES ===")
    try:
        form = await request.form()
        cfg = load_config()
        instruments = cfg.get("instruments", [])
        changes = False

        for idx, inst in enumerate(instruments):
            ticker = inst.get("ticker")
            for tf_name in AVAILABLE_TIMEFRAMES:
                # Ключи формы: strat_{idx}_{tf}, win_{idx}_{tf}
                strat_key = f"strat_{idx}_{tf_name}"
                win_key = f"win_{idx}_{tf_name}"

                if strat_key in form:
                    new_strategy = form.get(strat_key, "none")
                    new_window = form.get(win_key)
                    new_window = int(new_window) if new_window and new_window.isdigit() else None

                    tf_cfg = get_tf_config(inst, tf_name)
                    if tf_cfg:
                        if tf_cfg.get("strategy") != new_strategy:
                            logger.info(f"✅ {ticker}/{tf_name}: стратегия → {new_strategy}")
                            changes = True
                        if tf_cfg.get("strategy_window") != new_window:
                            changes = True
                        tf_cfg["strategy"] = new_strategy
                        if new_window is not None:
                            tf_cfg["strategy_window"] = new_window
                        elif "strategy_window" in tf_cfg:
                            del tf_cfg["strategy_window"]

        if changes and save_config(cfg):
            return HTMLResponse(content="<script>alert('✅ Стратегии сохранены!');location.href='/strategies';</script>")
        return HTMLResponse(content="<script>location.href='/strategies';</script>")

    except Exception as e:
        logger.error(f"💥 CRASH: {e}\n{traceback.format_exc()}")
        return HTMLResponse(content=f"<script>alert('💥 {e}');location.href='/strategies';</script>", status_code=500)


@app.post("/add")
async def add_ticker(t: str = Form(...), tf: str = Form(...), user: str = Depends(check_auth)):
    cfg = load_config()
    t = t.strip()
    if any(i.get("ticker") == t for i in cfg.get("instruments", [])):
        return HTMLResponse(content="<script>alert('⚠️ Уже есть');location.href='/';</script>")

    cfg.setdefault("instruments", []).append({
        "ticker": t, "enabled": True,
        "timeframes": [{
            "timeframe": tf, "enabled": True,
            "history_depth_days": TF_DEFAULTS[tf]["history_depth_days"],
            "update_interval_minutes": TF_DEFAULTS[tf]["update_interval_minutes"],
            "strategy": "none"
        }]
    })
    save_config(cfg)
    return HTMLResponse(content=f"<script>alert('✅ {t} добавлен');location.href='/';</script>")


def start_admin_ui(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    logger.info(f"🚀 Admin UI v3.0 (3 страницы) на {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info", access_log=False)


if __name__ == "__main__":
    start_admin_ui()

start_admin_ui()