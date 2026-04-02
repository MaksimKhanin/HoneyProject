import os, yaml, traceback
from fastapi import FastAPI, Request, HTTPException, Depends, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
from config_manager import get_config_manager
from logger import setup_logger
# 🔥 ИМПОРТИРУЕМ НАШ РЕЕСТР СТРАТЕГИЙ
from strategies import STRATEGY_REGISTRY

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


def check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != ADMIN_USER or credentials.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Access denied")
    return credentials.username


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


@app.get("/", response_class=HTMLResponse)
async def dashboard(user: str = Depends(check_auth)):
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

            # 🔥 Получаем текущую стратегию или дефолт
            current_strategy = tf_cfg.get("strategy", "none") if tf_cfg else "none"

            settings_block = ""
            if is_enabled and tf_cfg:
                hist_val = tf_cfg.get('history_depth_days', TF_DEFAULTS[tf_name]['history_depth_days'])
                int_val = tf_cfg.get('update_interval_minutes', TF_DEFAULTS[tf_name]['update_interval_minutes'])

                # 🔥 ГЕНЕРАЦИЯ СПИСКА СТРАТЕГИЙ
                strategy_options = ""
                for s_id, s_name in STRATEGY_REGISTRY.items():
                    selected = "selected" if s_id == current_strategy else ""
                    strategy_options += f'<option value="{s_id}" {selected}>{s_name}</option>'

                settings_block = f'''
                <div id="st_{idx}_{tf_name}" style="margin:6px 0;padding:6px;background:#2a2a2a;border-radius:4px;display:block;font-size:0.85em;border-top:1px solid #444;">
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-bottom:6px;">
                        <label>📅<input type="number" name="h_{idx}_{tf_name}" value="{hist_val}" style="width:100%;padding:3px;"></label>
                        <label>🔄<input type="number" name="i_{idx}_{tf_name}" value="{int_val}" style="width:100%;padding:3px;"></label>
                    </div>
                    <div style="margin-top:4px;">
                        <label style="font-size:0.9em;color:#aaa;">⚙️ Стратегия:</label>
                        <select name="s_{idx}_{tf_name}" style="width:100%;padding:4px;background:#333;color:#fff;border:1px solid #555;border-radius:3px;">
                            {strategy_options}
                        </select>
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
            if (settings) {
                // 🔥 Плавное появление/скрытие настроек
                settings.style.display = checkbox.checked ? 'block' : 'none';
            }
        }

        function toggleCard(header) {
            const body = header.parentElement.querySelector('.cb');
            body.style.display = body.style.display === 'none' ? 'block' : 'none';
        }

        // 🔥 При загрузке страницы скрываем настройки выключенных TF
        document.addEventListener('DOMContentLoaded', () => {
            document.querySelectorAll('[id^="st_"]').forEach(el => {
                const id = el.id.replace('st_', '');
                const cb = document.getElementById('cb_' + id);
                if (cb && !cb.checked) {
                    el.style.display = 'none';
                }
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
    <title>🎛 Honey Main Loader v2.0</title>
    <style>
        body{{background:#1a1a1a;color:#fff;padding:8px;font-family:system-ui}}
        .card{{margin-bottom:10px}}
        .tfb{{transition:all 0.2s}}
        .tfb.contrast{{background:#0d6efd;color:#fff;border:1px solid #0d6efd}}
        .tfb.secondary{{background:#444;color:#ccc;border:1px solid #555}}
        .big{{width:100%;padding:12px;font-size:1.1em;margin:15px 0}}
        input[type=number], select{{background:#333;border:1px solid #555;color:#fff;padding:4px;border-radius:3px;}}
        select{{width:100%;box-sizing:border-box;}}
    </style>
</head>
<body>
    <main class="container">
        <h3 style="text-align:center">📊 Инструменты и Стратегии</h3>
        <form action="/save" method="post" id="mainForm">
            {instruments_html}
            <button type="submit" class="big contrast">💾 Сохранить конфигурацию</button>
        </form>
        <article class="card" style="background:#252525;border:1px dashed #666;margin-top:15px;">
            <header><strong>➕ Добавить инструмент</strong></header>
            <form action="/add" method="post" style="display:grid;gap:8px;">
                <input type="text" name="t" placeholder="Тикер (например, SBER)" required style="padding:8px;">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                    <select name="tf" style="padding:8px;">
                        <option value="1d">1d (Дневки)</option><option value="1h">1h (Часовки)</option>
                        <option value="5m">5m (Пятиминутки)</option><option value="1m">1m (Скальпинг)</option>
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


@app.post("/save")
async def save_instruments(request: Request, user: str = Depends(check_auth)):
    logger.info("=== 🚨 SAVE START ===")
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
                    # Парсим цифры
                    h = form.get(f"h_{idx}_{tf}")
                    i_val = form.get(f"i_{idx}_{tf}")
                    new_hist = int(h) if h and h.isdigit() else TF_DEFAULTS[tf]["history_depth_days"]
                    new_int = int(i_val) if i_val and i_val.isdigit() else TF_DEFAULTS[tf]["update_interval_minutes"]

                    # 🔥 ПАРСИМ СТРАТЕГИЮ
                    new_strategy = form.get(f"s_{idx}_{tf}", "none")

                    existing = get_tf_config(inst, tf)
                    if existing:
                        # Проверяем изменения
                        if existing.get("strategy") != new_strategy:
                            logger.info(f"✅ {ticker}/{tf}: стратегия -> {new_strategy}")
                            changes = True
                        if existing.get("history_depth_days") != new_hist:
                            changes = True
                        if existing.get("update_interval_minutes") != new_int:
                            changes = True

                        existing.update({
                            "enabled": True,
                            "history_depth_days": new_hist,
                            "update_interval_minutes": new_int,
                            "strategy": new_strategy
                        })
                    else:
                        # Новый TF
                        inst.setdefault("timeframes", []).append({
                            "timeframe": tf,
                            "enabled": True,
                            "history_depth_days": new_hist,
                            "update_interval_minutes": new_int,
                            "strategy": new_strategy
                        })
                        logger.info(f"✅ {ticker}/{tf}: ДОБАВЛЕН (стратегия={new_strategy})")
                        changes = True
                else:
                    # Выключаем TF
                    for tcfg in inst.get("timeframes", []):
                        if tcfg.get("timeframe") == tf and tcfg.get("enabled"):
                            tcfg["enabled"] = False
                            changes = True
                            break

            # Логика авто-удаления
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

        if changes:
            if save_config(cfg):
                return HTMLResponse(
                    content="<script>alert('✅ Конфиг с стратегиями сохранён!');location.href='/';</script>")
        return HTMLResponse(content="<script>location.href='/';</script>")

    except Exception as e:
        logger.error(f"💥 CRASH: {e}\n{traceback.format_exc()}")
        return HTMLResponse(content=f"<script>alert('💥 {e}');location.href='/';</script>", status_code=500)


@app.post("/add")
async def add_ticker(t: str = Form(...), tf: str = Form(...), user: str = Depends(check_auth)):
    cfg = load_config()
    t = t.strip()
    if any(i.get("ticker") == t for i in cfg.get("instruments", [])):
        return HTMLResponse(content="<script>alert('⚠️ Уже есть');location.href='/';</script>")

    cfg.setdefault("instruments", []).append({
        "ticker": t,
        "enabled": True,
        "timeframes": [{
            "timeframe": tf,
            "enabled": True,
            "history_depth_days": TF_DEFAULTS[tf]["history_depth_days"],
            "update_interval_minutes": TF_DEFAULTS[tf]["update_interval_minutes"],
            "strategy": "none"  # 🔥 По умолчанию без стратегии
        }]
    })
    save_config(cfg)
    return HTMLResponse(content=f"<script>alert('✅ {t} добавлен');location.href='/';</script>")


def start_admin_ui(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    logger.info(f"🚀 Admin UI v2.0 на {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info", access_log=False)