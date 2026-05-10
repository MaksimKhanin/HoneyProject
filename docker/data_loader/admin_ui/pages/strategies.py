# admin_ui/pages/strategies.py
"""Страница привязки стратегий: обновление strategy_name/params в БД."""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from admin_ui.components.navbar import render_navbar
from admin_ui.core import (
    check_auth, get_db, get_all_instrument_configs, upsert_instrument_config,
    AVAILABLE_TIMEFRAMES, logger
)
import json

from .common_lib import HEAD_FIX

# 🔥 Авто-обнаружение стратегий
from admin_ui.components.strategy_discovery import discover_strategies, get_strategy_schema, render_param_field, render_param_field_custom

router = APIRouter()


def _render_strategy_card(cfg, strategies_registry):
    ticker = cfg["ticker"]
    tf_name = cfg["timeframe"]
    current_strategy = cfg.get("strategy_name") or "none"
    current_window = cfg.get("strategy_window")
    current_params = cfg.get("strategy_params") or {}
    live_enabled = cfg.get("live_trading_enabled", False)
    current_direction = current_params.get("direction", "ALL")

    strategy_cls = strategies_registry.get(current_strategy)
    params_schema = get_strategy_schema(strategy_cls) if strategy_cls else {}

    # 🔥 Рендерим поля параметров с УНИКАЛЬНЫМИ именами: param_{ticker}_{tf}_{param}
    params_fields_html = ""
    if params_schema and current_strategy != "none":
        for param_name, param_schema in params_schema.items():
            current_val = current_params.get(param_name)
            # 🔥 Имя поля теперь включает тикер и таймфрейм!
            field_name = f"param_{ticker}_{tf_name}_{param_name}"
            params_fields_html += render_param_field_custom(field_name, param_name, param_schema, current_val)
    else:
        # Фоллбэк: одно общее JSON-поле (тоже с префиксом)
        params_str = json.dumps(current_params, ensure_ascii=False, indent=2) if current_params else '{}'
        params_fields_html = f'''
        <div style="margin-bottom:8px;">
            <label style="font-size:0.85em;color:var(--text-secondary);">⚙️ Параметры (JSON)</label>
            <textarea name="params_json_{ticker}_{tf_name}" rows="4" placeholder='{{"param": value}}' style="width:100%;padding:8px;background:var(--bg-input);color:var(--text-primary);border:1px solid var(--border-color);border-radius:4px;font-family:monospace;font-size:0.9em;">{params_str}</textarea>
        </div>
        '''

    strategy_options = "".join(
        f'<option value="{s_name}" {"selected" if s_name == current_strategy else ""}>{s_name}</option>'
        for s_name in strategies_registry.keys()
    )

    return f'''
    <article class="strategy-card" data-ticker="{ticker}" data-tf="{tf_name}" style="background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:8px;padding:16px;margin:0 0 16px 0;">
        <!-- Заголовок (без изменений) -->
        <header style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border-color);flex-wrap:wrap;gap:10px;">
            <div style="display:flex;align-items:center;gap:10px;">
                <strong style="font-size:1.2em;color:var(--text-primary);">{ticker}</strong>
                <small style="color:var(--text-secondary);background:var(--bg-tertiary);padding:3px 10px;border-radius:4px;font-weight:500;">{tf_name}</small>
            </div>
            <code style="background:var(--accent);color:#fff;padding:4px 12px;border-radius:20px;font-size:0.85em;font-weight:500;">{current_strategy}</code>
        </header>

        <!-- Поля формы -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;">
            <!-- Стратегия -->
            <div>
                <label style="display:block;font-size:0.9em;color:var(--text-secondary);margin-bottom:6px;font-weight:500;">🧠 Стратегия</label>
                <select name="strat_{ticker}_{tf_name}" class="strategy-select" style="width:100%;padding:10px;background:var(--bg-input);color:var(--text-primary);border:1px solid var(--border-color);border-radius:6px;font-size:1em;min-height:44px;box-sizing:border-box;">
                    <option value="none">— нет —</option>
                    {strategy_options}
                </select>
            </div>
            <!-- Окно -->
            <div>
                <label style="display:block;font-size:0.9em;color:var(--text-secondary);margin-bottom:6px;font-weight:500;">🪟 Окно</label>
                <input type="number" name="win_{ticker}_{tf_name}" value="{current_window or ''}" placeholder="авто" min="5" max="500" style="width:100%;padding:10px;background:var(--bg-input);color:var(--text-primary);border:1px solid var(--border-color);border-radius:6px;font-size:1em;min-height:44px;text-align:center;box-sizing:border-box;">
            </div>
            <!-- Live Toggle -->
            <div style="display:flex;align-items:center;gap:8px;">
                <input type="checkbox" id="live_{ticker}_{tf_name}" name="live_{ticker}_{tf_name}" value="true" {"checked" if live_enabled else ""} style="width:18px;height:18px;cursor:pointer;accent-color:var(--danger);">
                <label for="live_{ticker}_{tf_name}" style="font-size:0.9em;color:var(--text-primary);cursor:pointer;font-weight:500;">🔴 Live</label>
            </div>
            <small style="grid-column:1/-1;color:var(--text-secondary);font-size:0.8em;">
                {"⚠️ Live: ордера" if live_enabled else "🐕 Watchdog: только уведомления"}
            </small>

            <!-- 🔥 Динамические поля параметров (с уникальными именами) -->
            <div style="grid-column:1/-1;border-top:1px dashed var(--border-color);padding-top:12px;">
                <label style="display:block;font-size:0.9em;color:var(--text-secondary);margin-bottom:8px;font-weight:500;">⚙️ Параметры</label>
                {params_fields_html}
            </div>
        </div>
    </article>
    '''

@router.get("/strategies", response_class=HTMLResponse)
async def page_strategies(user: str = Depends(check_auth), db=Depends(get_db)):
    configs = get_all_instrument_configs(db)

    # 🔥 Авто-обнаружение стратегий
    strategies_registry = discover_strategies()
    logger.info(f"🔍 Найдено стратегий: {list(strategies_registry.keys())}")

    cards_html = ""
    for cfg in configs:
        cards_html += _render_strategy_card(cfg, strategies_registry)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css">
    <title>🧠 Стратегии | Honey Loader</title>
    {HEAD_FIX}
    <style>
        :root {{
            --bg-primary: #1a1a1a; --bg-secondary: #252525; --bg-tertiary: #2a2a2a;
            --bg-input: #333; --border-color: #444; --text-primary: #fff;
            --text-secondary: #aaa; --accent: #0d6efd; --accent-hover: #0b5ed7;
            --danger: #dc3545; --warning: #ffc107;
        }}
        body {{ background: var(--bg-primary) !important; color: var(--text-primary) !important; font-family: system-ui, -apple-system, sans-serif; }}
        .strategies-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px; margin: 0 -8px; padding: 0 8px; }}
        .strategy-card {{ background: var(--bg-secondary) !important; border: 1px solid var(--border-color) !important; border-radius: 8px; padding: 16px; margin: 0 !important; transition: box-shadow 0.2s, border-color 0.2s; }}
        .strategy-card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.3); border-color: var(--accent) !important; }}
        .strategy-select, .strategy-card input, .strategy-card textarea {{ background: var(--bg-input) !important; color: var(--text-primary) !important; border: 1px solid var(--border-color) !important; border-radius: 6px; font-size: 1em; min-height: 44px; padding: 10px 12px; width: 100%; box-sizing: border-box; }}
        .strategy-select:focus, .strategy-card input:focus, .strategy-card textarea:focus {{ outline: none; border-color: var(--accent) !important; box-shadow: 0 0 0 3px rgba(13, 110, 253, 0.2); }}
        .btn-save {{ background: var(--accent) !important; color: #fff !important; border: none !important; border-radius: 8px; padding: 14px 24px; font-size: 1.05em; font-weight: 600; cursor: pointer; transition: background 0.2s; width: 100%; margin-top: 8px; min-height: 48px; }}
        .btn-save:hover {{ background: var(--accent-hover) !important; }}
        .help-card {{ background: var(--bg-secondary) !important; border: 1px dashed var(--border-color) !important; border-radius: 8px; padding: 16px; margin-top: 24px; }}
        .help-card ul {{ margin: 0; padding-left: 20px; color: var(--text-secondary); }}
        .help-card code {{ background: var(--bg-tertiary); padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
        @keyframes highlight {{ 0% {{ background: rgba(13, 110, 253, 0.2); }} 100% {{ background: var(--bg-secondary); }} }}
        .strategy-card.changed {{ animation: highlight 2s ease-out; border-color: var(--accent) !important; }}
        /* Toggle стиль */
        .live-toggle {{ display: flex; align-items: center; gap: 8px; }}
        .live-toggle input[type="checkbox"] {{ width: 18px; height: 18px; cursor: pointer; accent-color: var(--danger); }}
        .live-toggle label {{ cursor: pointer; font-weight: 500; }}
        .live-warning {{ color: var(--warning); font-size: 0.8em; }}
        @media (max-width: 480px) {{ .strategies-container {{ grid-template-columns: 1fr; }} .strategy-card header {{ flex-direction: column; align-items: flex-start; }} }}
    </style>
</head>
<body>
    <main class="container" style="padding: 12px 8px;">
        {render_navbar("/strategies")}
        <article class="card" style="background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
            <header style="margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--border-color);">
                <strong style="font-size: 1.3em; color: var(--text-primary);">🎯 Привязка стратегий</strong>
            </header>
            <form action="/save_strategies" method="post" id="strategiesForm">
                <div class="strategies-container">{cards_html}</div>
                <button type="submit" class="btn-save">💾 Сохранить все стратегии</button>
            </form>
        </article>
        <article class="help-card">
            <header style="margin-bottom: 12px; font-weight: 600; color: var(--text-primary);">ℹ️ Справка</header>
            <ul>
                <li><strong>Live Trading</strong> — если включено, стратегия будет отправлять реальные ордера (через заглушку пока). Если выключено — только уведомления в TG (режим <code>watchdog</code>).</li>
                <li><strong>Направление</strong> — <code>BUY_ONLY</code> (только лонг), <code>SHORT_ONLY</code> (только шорт), <code>ALL</code> (оба направления).</li>
                <li><strong>Параметры</strong> — JSON, например: <code>{{"min_pullback": 0.03, "TSL": 0.05}}</code>. Поле <code>direction</code> добавляется автоматически из выпадашки, но можно переопределить здесь.</li>
                <li>Стратегии доступны из папки <code>strategies/</code> автоматически — добавь новый файл с классом <code>BaseStrategy</code>, и он появится в списке.</li>
            </ul>
        </article>
    </main>
    <script>
    
    
        // Подсветка изменённых карточек
document.querySelectorAll('select[name^="strat_"]').forEach(select => {{
    select.addEventListener('change', async function() {{
        const card = this.closest('.strategy-card');
        const ticker = card.dataset.ticker;
        const tf = card.dataset.tf;
        const strategyName = this.value;
        const paramsContainer = card.querySelector('[style*="grid-column:1/-1"]');
        
        if (!strategyName || strategyName === 'none') {{
            // Сброс к дефолтному JSON-полю
            paramsContainer.innerHTML = `
                <div style="margin-bottom:8px;">
                    <label style="font-size:0.85em;color:var(--text-secondary);">⚙️ Параметры (JSON)</label>
                    <textarea name="params_json_${{ticker}}_${{tf}}" rows="4" placeholder='{{"param": value}}' style="width:100%;padding:8px;background:var(--bg-input);color:var(--text-primary);border:1px solid var(--border-color);border-radius:4px;font-family:monospace;font-size:0.9em;">{{}}</textarea>
                </div>
            `;
            return;
        }}
        
        try {{
            const response = await fetch(`/api/strategy_schema/${{strategyName}}`);
            const data = await response.json();
            
            if (data.schema && Object.keys(data.schema).length > 0) {{
                let fieldsHtml = '';
                for (const [paramName, paramSchema] of Object.entries(data.schema)) {{
                    const ptype = paramSchema.type || 'string';
                    const defaultVal = paramSchema.default ?? '';
                    const desc = paramSchema.desc || '';
                    // 🔥 Уникальное имя поля: param_{{ticker}}_{{tf}}_{{param}}
                    const fieldName = `param_${{ticker}}_${{tf}}_${{paramName}}`;
                    
                    if (ptype === 'select' && paramSchema.options) {{
                        const options = paramSchema.options.map(opt => 
                            `<option value="${{opt}}" ${{opt === defaultVal ? 'selected' : ''}}>${{opt}}</option>`
                        ).join('');
                        fieldsHtml += `
                            <div style="margin-bottom:8px;">
                                <label style="font-size:0.85em;color:var(--text-secondary);">${{paramName}}</label>
                                <select name="${{fieldName}}" style="width:100%;padding:8px;background:var(--bg-input);color:var(--text-primary);border:1px solid var(--border-color);border-radius:4px;">
                                    ${{options}}
                                </select>
                                ${{desc ? `<small style="color:var(--text-secondary);font-size:0.8em;">${{desc}}</small>` : ''}}
                            </div>
                        `;
                    }} else if (ptype === 'bool') {{
                        fieldsHtml += `
                            <div style="margin-bottom:8px;display:flex;align-items:center;gap:8px;">
                                <input type="checkbox" name="${{fieldName}}" value="true" ${{defaultVal ? 'checked' : ''}} id="${{fieldName}}">
                                <label for="${{fieldName}}" style="font-size:0.9em;color:var(--text-primary);">${{paramName}}</label>
                                ${{desc ? `<small style="color:var(--text-secondary);font-size:0.8em;margin-left:auto;">${{desc}}</small>` : ''}}
                            </div>
                        `;
                    }} else if (ptype === 'int' || ptype === 'float') {{
                        const step = ptype === 'int' ? '1' : '0.01';
                        const min = paramSchema.min ?? (ptype === 'int' ? 1 : '');
                        const max = paramSchema.max ?? '';
                        fieldsHtml += `
                            <div style="margin-bottom:8px;">
                                <label style="font-size:0.85em;color:var(--text-secondary);">${{paramName}}</label>
                                <input type="number" name="${{fieldName}}" value="${{defaultVal}}" step="${{step}}" min="${{min}}" max="${{max}}" style="width:100%;padding:8px;background:var(--bg-input);color:var(--text-primary);border:1px solid var(--border-color);border-radius:4px;">
                                ${{desc ? `<small style="color:var(--text-secondary);font-size:0.8em;">${{desc}}</small>` : ''}}
                            </div>
                        `;
                    }} else {{
                        fieldsHtml += `
                            <div style="margin-bottom:8px;">
                                <label style="font-size:0.85em;color:var(--text-secondary);">${{paramName}}</label>
                                <input type="text" name="${{fieldName}}" value="${{defaultVal}}" style="width:100%;padding:8px;background:var(--bg-input);color:var(--text-primary);border:1px solid var(--border-color);border-radius:4px;">
                                ${{desc ? `<small style="color:var(--text-secondary);font-size:0.8em;">${{desc}}</small>` : ''}}
                            </div>
                        `;
                    }}
                }}
                paramsContainer.innerHTML = `
                    <label style="display:block;font-size:0.9em;color:var(--text-secondary);margin-bottom:8px;font-weight:500;">⚙️ Параметры</label>
                    ${{fieldsHtml}}
                    <small style="color:var(--text-secondary);font-size:0.8em;">Поля сгенерированы автоматически</small>
                `;
            }} else {{
                paramsContainer.innerHTML = `
                    <div style="margin-bottom:8px;">
                        <label style="font-size:0.85em;color:var(--text-secondary);">⚙️ Параметры (JSON)</label>
                        <textarea name="params_json_${{ticker}}_${{tf}}" rows="4" placeholder='{{}}' style="width:100%;padding:8px;background:var(--bg-input);color:var(--text-primary);border:1px solid var(--border-color);border-radius:4px;font-family:monospace;font-size:0.9em;">{{}}</textarea>
                    </div>
                `;
            }}
        }} catch (e) {{
            console.error('Failed to fetch strategy schema:', e);
            paramsContainer.innerHTML = `
                <div style="margin-bottom:8px;">
                    <label style="font-size:0.85em;color:var(--text-secondary);">⚙️ Параметры (JSON)</label>
                    <textarea name="params_json_${{ticker}}_${{tf}}" rows="4" placeholder='{{}}' style="width:100%;padding:8px;background:var(--bg-input);color:var(--text-primary);border:1px solid var(--border-color);border-radius:4px;font-family:monospace;font-size:0.9em;">{{}}</textarea>
                </div>
            `;
        }}
    }});
}});

// 🔥 Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {{
    document.querySelectorAll('select[name^="strat_"]').forEach(select => {{
        if (select.value && select.value !== 'none') {{
            select.dispatchEvent(new Event('change'));
        }}
    }});
}});

        // Валидация JSON + авто-добавление direction
        document.querySelectorAll('textarea[name^="params_"]').forEach(el => {{
            el.addEventListener('blur', function() {{
                if (!this.value.trim()) return;
                try {{
                    let params = JSON.parse(this.value);
                    // Если direction не указан — добавляем дефолт (опционально)
                    if (!params.direction) params.direction = "ALL";
                    this.value = JSON.stringify(params, null, 2);
                    this.style.borderColor = '#0f0';
                    this.title = '✅ Валидный JSON';
                }} catch (e) {{
                    this.style.borderColor = '#f44';
                    this.title = `❌ Ошибка: ${{e.message}}`;
                }}
            }});
        }});

        // Предупреждение при включении Live Trading
        document.querySelectorAll('input[name^="live_"]').forEach(cb => {{
            cb.addEventListener('change', function() {{
                const card = this.closest('.strategy-card');
                const ticker = card.dataset.ticker;
                const tf = card.dataset.tf;
                const hint = card.querySelector('small.live-warning') || (() => {{
                    const h = document.createElement('small');
                    h.className = 'live-warning';
                    h.style.gridColumn = '1/-1';
                    card.querySelector('div[style*="grid-column:1/-1"]').after(h);
                    return h;
                }})();
                if (this.checked) {{
                    hint.textContent = `⚠️ ${{ticker}}/${{tf}}: будет отправлять ордера! Убедись, что параметры риска настроены.`;
                    hint.style.color = 'var(--warning)';
                }} else {{
                    hint.textContent = '';
                }}
            }});
        }});
    </script>
</body>
</html>"""
    return html


@router.post("/save_strategies")
async def save_strategies(request: Request, user: str = Depends(check_auth), db=Depends(get_db)):
    logger.info("=== 🚨 SAVE STRATEGIES ===")
    try:
        form = await request.form()
        configs = get_all_instrument_configs(db)

        from admin_ui.components.strategy_discovery import discover_strategies, get_strategy_schema
        strategies_registry = discover_strategies()

        changes = 0

        for cfg in configs:
            ticker = cfg["ticker"]
            tf_name = cfg["timeframe"]
            strat_key = f"strat_{ticker}_{tf_name}"

            if strat_key not in form:
                continue

            new_strategy = form.get(strat_key, "none")
            new_window = form.get(f"win_{ticker}_{tf_name}")
            new_window = int(new_window) if new_window and new_window.isdigit() else None

            # 🔥 Инициализация параметров
            new_params = {}

            # 🔹 Если стратегия "none" — параметры не собираем
            if new_strategy == "none":
                new_params = {}
            else:
                strategy_cls = strategies_registry.get(new_strategy)
                params_schema = get_strategy_schema(strategy_cls) if strategy_cls else {}

                # 🔥 Собираем ТОЛЬКО поля с префиксом этого тикера/таймфрейма
                if params_schema:
                    for param_name in params_schema.keys():
                        # 🔥 Ищем поле с уникальным именем: param_{ticker}_{tf}_{param}
                        field_name = f"param_{ticker}_{tf_name}_{param_name}"
                        if field_name in form:
                            raw_val = form.get(field_name)
                            ptype = params_schema[param_name].get("type", "string")

                            if ptype == "int" and raw_val not in (None, ""):
                                new_params[param_name] = int(raw_val)
                            elif ptype == "float" and raw_val not in (None, ""):
                                new_params[param_name] = float(raw_val)
                            elif ptype == "bool":
                                new_params[param_name] = raw_val == "true"
                            elif raw_val not in (None, ""):
                                new_params[param_name] = raw_val

                # 🔹 Фоллбэк: если схема не сработала, пробуем прочитать из общего JSON-поля
                if not new_params:
                    params_json = form.get(f"params_json_{ticker}_{tf_name}", "").strip()
                    if params_json:
                        try:
                            new_params = json.loads(params_json)
                        except json.JSONDecodeError:
                            logger.warning(f"⚠️ Неверный JSON для {ticker}/{tf_name}")

            # 🔥 direction и live_trading_enabled
            dir_key = f"dir_{ticker}_{tf_name}"
            live_key = f"live_{ticker}_{tf_name}"

            direction_from_ui = form.get(dir_key, "ALL")
            if direction_from_ui in ("BUY_ONLY", "SHORT_ONLY", "ALL"):
                new_params["direction"] = direction_from_ui

            live_enabled = form.get(live_key) == "true"

            # Сравниваем и сохраняем
            old_strategy = cfg.get("strategy_name") or "none"
            old_window = cfg.get("strategy_window")
            old_params = cfg.get("strategy_params") or {}
            old_live = cfg.get("live_trading_enabled", False)

            if (old_strategy != new_strategy or
                    old_window != new_window or
                    old_params != new_params or
                    old_live != live_enabled):

                success = upsert_instrument_config(
                    db=db,
                    ticker=ticker,
                    timeframe=tf_name,
                    enabled=cfg.get("enabled", True),
                    history_depth_days=cfg.get("history_depth_days"),
                    update_interval_minutes=cfg.get("update_interval_minutes"),
                    strategy_name=new_strategy,
                    strategy_window=new_window,
                    strategy_params=new_params if new_params else None,
                    live_trading_enabled=live_enabled
                )

                if success:
                    changes += 1
                    logger.info(
                        f"✅ {ticker}/{tf_name}: strategy='{new_strategy}', "
                        f"window={new_window}, direction={new_params.get('direction')}, live={live_enabled}, "
                        f"params={new_params}"
                    )

        logger.info(f"💾 Сохранено изменений стратегий: {changes}")
        return HTMLResponse(content="<script>alert('✅ Стратегии сохранены!');location.href='/strategies';</script>")

    except Exception as e:
        logger.error(f"💥 CRASH: {e}", exc_info=True)
        return HTMLResponse(content=f"<script>alert('💥 {e}');location.href='/strategies';</script>", status_code=500)