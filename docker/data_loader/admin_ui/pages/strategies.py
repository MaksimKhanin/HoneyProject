# admin_ui/pages/strategies.py
"""Страница привязки стратегий к таймфреймам."""

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasicCredentials

from admin_ui.components.navbar import render_navbar
from admin_ui.components.theme import render_head
from admin_ui.core import (
    check_auth, load_config, save_config, get_tf_config,
    AVAILABLE_TIMEFRAMES, logger
)
from strategy import STRATEGY_REGISTRY

router = APIRouter()


@router.get("/strategies", response_class=HTMLResponse)
async def page_strategies(user: str = Depends(check_auth)):
    cfg = load_config()
    instruments = cfg.get("instruments", [])
    rows_html = ""

    for idx, inst in enumerate(instruments):
        ticker = inst.get("ticker", "UNKNOWN")
        for tf_name in AVAILABLE_TIMEFRAMES:
            tf_cfg = get_tf_config(inst, tf_name)
            if not tf_cfg or not tf_cfg.get("enabled", False):
                continue
            current_strategy = tf_cfg.get("strategy", "none")
            strategy_options = ""
            for s_id, s_name in STRATEGY_REGISTRY.items():
                selected = "selected" if s_id == current_strategy else ""
                strategy_options += f'<option value="{s_id}" {selected}>{s_name}</option>'
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
        {render_navbar("/strategies")}
        <article class="card" style="background:#252525;border:1px solid #444;">
            <header><strong>🎯 Привязка стратегий</strong></header>
            <form action="/save_strategies" method="post">
                <table>
                    <thead><tr><th>Тикер</th><th>Таймфрейм</th><th>Стратегия</th><th>Окно (свечи)</th></tr></thead>
                    <tbody>
                        {rows_html if rows_html else '<tr><td colspan="4" style="text-align:center;color:#777;">Нет активных таймфреймов</td></tr>'}
                    </tbody>
                </table>
                <button type="submit" class="big contrast" style="margin-top:15px;">💾 Сохранить стратегии</button>
            </form>
        </article>
        <article class="card" style="background:#252525;border:1px dashed #666;margin-top:15px;">
            <header><strong>ℹ️ Справка</strong></header>
            <ul style="font-size:0.9em;color:#fff;">
                <li><code>Окно</code> — сколько последних свечей использовать для расчёта (оставь пустым для авто)</li>
                <li>Стратегии запускаются только на <strong>активных</strong> таймфреймах</li>
                <li>Сигналы пишутся в таблицу <code>signals</code> и дублируются в Телеграм</li>
            </ul>
        </article>
    </main>
</body>
</html>"""
    return html


@router.post("/save_strategies")
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