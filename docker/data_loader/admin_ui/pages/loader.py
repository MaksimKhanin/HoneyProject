# admin_ui/pages/loader.py
"""Страница настроек загрузки: инструменты, таймфреймы, интервалы."""

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasicCredentials
import os, yaml, traceback

# Импорты из родительского пакета
from admin_ui.components.navbar import render_navbar
from admin_ui.core import (
    check_auth, load_config, save_config, get_tf_config,
    TF_DEFAULTS, AVAILABLE_TIMEFRAMES, logger
)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
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
    body{{background:#1a1a1a!important;color:#fff!important;padding:8px;font-family:system-ui}}
    .card,article{{background:#252525!important;border:1px solid #444!important;color:#fff!important;margin-bottom:10px}}
    .card>header,article>header, .card header, article header{{
        color:#ffffff!important;
        background:#2a2a2a!important;
        border-bottom:1px solid #444!important
    }}
    .card>header strong,article>header strong,.card header strong,article header strong,
    .card>header b,article>header b,.card header b,article header b{{
        color:#ffffff!important
    }}
    table{{background:#252525!important;color:#fff!important;border-collapse:collapse;width:100%}}
    table th{{background:#2a2a2a!important;color:#fff!important;border-bottom:2px solid #444!important}}
    table td{{background:#252525!important;color:#fff!important;border-bottom:1px solid #333!important}}
    input,select,button{{background:#333!important;color:#fff!important;border:1px solid #555!important}}
    .contrast{{background:#0d6efd!important;color:#fff!important}}
    .secondary{{background:#444!important;color:#ccc!important}}
    a{{color:#0d6efd!important}}
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


@router.post("/save")
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
                        if existing.get("history_depth_days") != new_hist or existing.get("update_interval_minutes") != new_int:
                            changes = True
                        existing.update({"enabled": True, "history_depth_days": new_hist, "update_interval_minutes": new_int})
                    else:
                        inst.setdefault("timeframes", []).append({
                            "timeframe": tf, "enabled": True,
                            "history_depth_days": new_hist, "update_interval_minutes": new_int, "strategy": "none"
                        })
                        changes = True
                else:
                    for tcfg in inst.get("timeframes", []):
                        if tcfg.get("timeframe") == tf and tcfg.get("enabled"):
                            tcfg["enabled"] = False
                            changes = True
                            break
            enabled_tfs = [tf for tf in inst.get("timeframes", []) if tf.get("enabled", False)]
            if len(enabled_tfs) == 0 and inst.get("timeframes"):
                inst["_del"] = True
                changes = True

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


@router.post("/add")
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