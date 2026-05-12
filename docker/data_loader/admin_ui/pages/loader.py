# admin_ui/pages/loader.py
"""Страница настроек загрузки: управление instrument_config в БД."""

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from admin_ui.components.navbar import render_navbar
from admin_ui.core import (
    check_auth, get_db, get_all_instrument_configs, get_instrument_config,
    upsert_instrument_config, toggle_instrument_enabled,
    delete_instrument_config, delete_instrument_configs_by_ticker,
    TF_DEFAULTS, AVAILABLE_TIMEFRAMES, logger
)

from .common_lib import HEAD_FIX

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def page_loader(user: str = Depends(check_auth), db=Depends(get_db)):
    """Главная страница: список инструментов из БД."""
    configs = get_all_instrument_configs(db)

    # Группируем по тикеру для отображения
    by_ticker = {}
    for cfg in configs:
        ticker = cfg["ticker"]
        if ticker not in by_ticker:
            by_ticker[ticker] = []
        by_ticker[ticker].append(cfg)

    instruments_html = ""

    # Генерируем HTML только если есть данные
    for ticker, tfs in by_ticker.items():
        # Кнопка удаления всего тикера (мягкая: выключает все TF)
        delete_btn = f'''
        <button type="button" class="secondary" 
                onclick="if(confirm('⚠️ УДАЛИТЬ {ticker}?\\n\\nЭто удалит ВСЕ таймфреймы и сигналы для этого инструмента.\\n\\nПродолжить?')) 
                         fetch('/delete_ticker?t={ticker}', {{method:'POST'}}).then(()=>location.reload())"
                style="padding:2px 6px;font-size:0.7em;margin-left:8px;color:#f44;border-color:#f44;"
                title="🗑️ Полностью удалить инструмент из БД">🗑️</button>
        '''

        tf_buttons = ""
        for cfg in tfs:
            tf_name = cfg["timeframe"]
            is_enabled = cfg.get("enabled", True)

            # Настройки под каждым таймфреймом
            hist_val = cfg.get("history_depth_days") or TF_DEFAULTS[tf_name]["history_depth_days"]
            int_val = cfg.get("update_interval_minutes") or TF_DEFAULTS[tf_name]["update_interval_minutes"]

            settings_block = f'''
            <div id="st_{ticker}_{tf_name}" style="margin:6px 0;padding:6px;background:#2a2a2a;border-radius:4px;display:block;font-size:0.85em;border-top:1px solid #444;">
                <div style="display:grid;grid-template-columns:1fr 1fr auto;gap:4px;align-items:center;"> 
                    <label style="display:flex;align-items:center;gap:4px;">
                        📅<input type="number" name="h_{ticker}_{tf_name}" value="{hist_val}" min="1" max="3650" 
                               style="width:100%;padding:3px;" title="Глубина истории (дни)"
                               data-ticker="{ticker}" data-timeframe="{tf_name}" data-type="hist">
                    </label>
                    <label style="display:flex;align-items:center;gap:4px;">
                        🔄<input type="number" name="i_{ticker}_{tf_name}" value="{int_val}" min="1" max="1440" 
                               style="width:100%;padding:3px;" title="Интервал обновления (мин)"
                               data-ticker="{ticker}" data-timeframe="{tf_name}" data-type="int">
                    </label>
                </div>
                <div id="status_{ticker}_{tf_name}" style="font-size:0.75em;color:#aaa;margin-top:4px;text-align:right;"></div>
            </div>
            '''

            btn_class = "contrast" if is_enabled else "secondary"
            checked_str = "checked" if is_enabled else ""
            tf_buttons += f'''
            <div style="text-align:center;margin:3px 0;">
                <input type="checkbox" id="cb_{ticker}_{tf_name}" name="e_{ticker}_{tf_name}" style="display:none;" {checked_str} 
                       onchange="fetch('/toggle_tf', {{
                           method:'POST',
                           headers:{{'Content-Type':'application/x-www-form-urlencoded'}},
                           body:`t={ticker}&tf={tf_name}&enabled=${{this.checked?1:0}}`
                       }}).catch(e=>alert('Ошибка: '+e))">
                <span class="tfb {btn_class}" style="display:inline-block;padding:5px 8px;border-radius:4px;font-size:0.8em;cursor:pointer;width:100%;box-sizing:border-box;"
                      onclick="toggleTF(event, '{ticker}_{tf_name}')">{tf_name}</span>
                {settings_block}
            </div>
            '''

        instruments_html += f'''
        <article class="card" style="margin-bottom:10px;background:#252525;border:1px solid #444;">
            <header style="display:flex;justify-content:space-between;align-items:center;padding:10px;cursor:pointer;" onclick="toggleCard(this)">
                <div>
                    <strong style="font-size:1.1em;">{ticker}</strong>
                    {delete_btn}
                </div>
            </header>
            <div class="cb" style="padding:0 10px 10px;">
                <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:3px;margin:8px 0;">
                    {tf_buttons}
                </div>
            </div>
        </article>
        '''

    # JS для интерактива
    js_code = """
    <script>
        function toggleCard(header) {
            const body = header.parentElement.querySelector('.cb');
            body.style.display = body.style.display === 'none' ? 'block' : 'none';
        }

        function toggleSettings(id) {
            const settings = document.getElementById('st_' + id);
            if (settings) {
                const isVisible = settings.style.display === 'block';
                settings.style.display = isVisible ? 'none' : 'block';
                if (!isVisible && window.innerWidth < 768) {
                    settings.scrollIntoView({behavior: 'smooth', block: 'center'});
                }
            }
        }

        function toggleTF(event, id) {
            event?.stopPropagation(); 
            const checkbox = document.getElementById('cb_' + id);
            if (!checkbox) return;
            checkbox.checked = !checkbox.checked;
            checkbox.dispatchEvent(new Event('change'));

            const span = event?.currentTarget;
            if (span) {
                span.classList.toggle('contrast', checkbox.checked);
                span.classList.toggle('secondary', !checkbox.checked);
            }
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

    js_save_button = """
<script>
async function saveSettings(ticker, timeframe, btnElement) {
    const statusEl = document.getElementById(`status_${ticker}_${timeframe}`);
    const histInput = document.querySelector(`input[name="h_${ticker}_${timeframe}"]`);
    const intInput = document.querySelector(`input[name="i_${ticker}_${timeframe}"]`);

    if (btnElement) {
        const originalText = btnElement.innerHTML;
        btnElement.innerHTML = '⏳';
        btnElement.disabled = true;
    }
    if (statusEl) statusEl.textContent = 'Сохранение...';

    const payload = new URLSearchParams();
    payload.append('ticker', ticker);
    payload.append('timeframe', timeframe);
    if (histInput) payload.append('history_depth_days', histInput.value);
    if (intInput) payload.append('update_interval_minutes', intInput.value);

    try {
        const resp = await fetch('/save_settings', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: payload
        });

        const result = await resp.json();

        if (result.ok) {
            if (statusEl) {
                statusEl.textContent = '✅ Сохранено';
                statusEl.style.color = '#0f0';
            }
            [histInput, intInput].forEach(inp => {
                if (inp) {
                    const orig = inp.style.background;
                    inp.style.background = '#0f03';
                    setTimeout(() => inp.style.background = orig, 300);
                }
            });
        } else {
            const msg = `❌ Ошибка: ${result.error}`;
            if (statusEl) {
                statusEl.textContent = msg;
                statusEl.style.color = '#f44';
            }
            alert(msg);
        }
    } catch (err) {
        const msg = `🌐 Ошибка сети: ${err.message}`;
        if (statusEl) {
            statusEl.textContent = msg;
            statusEl.style.color = '#f44';
        }
        alert(msg);
    } finally {
        if (btnElement) {
            btnElement.innerHTML = '💾';
            btnElement.disabled = false;
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input[name^="h_"], input[name^="i_"]').forEach(input => {
        input.addEventListener('change', (e) => {
            const ticker = e.target.dataset.ticker;
            const timeframe = e.target.dataset.timeframe;
            if (ticker && timeframe) {
                saveSettings(ticker, timeframe, null);
            }
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                input.blur();
            }
        });
    });
});
</script>
    """

    # Формируем финальный HTML
    instruments_section = instruments_html if instruments_html else '<p style="color:#777;text-align:center;padding:20px;">Нет активных инструментов. Добавьте первый выше 👆</p>'

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css">
    <title>📥 Настройки загрузки | Honey Loader</title>
    {HEAD_FIX}
</head>
<body>
    <main class="container">
        {render_navbar("/")}

        <!-- Форма добавления нового инструмента -->
        <article class="card" style="background:#252525;border:1px dashed #666;margin-bottom:15px;">
            <header><strong>➕ Добавить инструмент</strong></header>
            <form action="/add" method="post" style="display:grid;gap:8px;">
                <input type="text" name="t" placeholder="Тикер (например, SBER)" required style="padding:8px;">
                    <div style="display:grid;grid-template-columns:1fr auto;gap:8px;"> 
                        <select name="tf" style="padding:8px;">
                            {''.join(f'<option value="{tf}">{tf}</option>' for tf in AVAILABLE_TIMEFRAMES)}
                        </select>
                        <button type="submit" class="contrast" style="padding:8px;">➕ Добавить</button>
                    </div>
            </form>
        </article>

        <!-- Список инструментов -->
        {instruments_section}
    </main>
    {js_code}
    {js_save_button}
</body>
</html>"""
    return html


@router.post("/add")
async def add_instrument(
        t: str = Form(...),
        tf: str = Form(...),
        user: str = Depends(check_auth),
        db=Depends(get_db)
):
    """Добавляет НОВЫЙ инструмент ИЛИ включает существующий отключенный."""
    t = t.strip().upper()
    tf = tf.lower()
    logger.info(f"🔍 Попытка добавить: {t}/{tf}")

    # Проверяем, есть ли запись в БД (любая, даже отключенная)
    try:
        existing = db.get_instrument_config(t, tf)
    except Exception as e:
        logger.error(f"❌ Ошибка проверки существующего конфига: {e}", exc_info=True)
        return HTMLResponse(
            content=f"<script>alert('❌ Ошибка БД: {e}');location.href='/';</script>",
            status_code=500
        )

    if existing:
        if not existing.get("enabled", True):
            logger.info(f"🔄 {t}/{tf} найден, но отключен → включаем")
            success = toggle_instrument_enabled(db, t, tf, enabled=True)
            if success:
                logger.info(f"✅ Включён ранее отключенный {t}/{tf}")
                return HTMLResponse(
                    content=f"<script>alert('✅ {t}/{tf} включён (был отключен)');location.href='/';</script>"
                )
            else:
                logger.error(f"❌ Не удалось включить {t}/{tf}")
                return HTMLResponse(
                    content=f"<script>alert('❌ Ошибка включения {t}/{tf}');location.href='/';</script>",
                    status_code=500
                )
        else:
            logger.info(f"ℹ️ {t}/{tf} уже активен")
            return HTMLResponse(
                content=f"<script>alert('ℹ️ {t}/{tf} уже активен');location.href='/';</script>"
            )

    # 🆕 Создаём новую запись
    logger.info(f"🆕 Создаём новый конфиг: {t}/{tf}")
    defaults = TF_DEFAULTS.get(tf, {})

    try:
        success = upsert_instrument_config(
            db=db,
            ticker=t,
            timeframe=tf,
            enabled=True,
            history_depth_days=defaults.get("history_depth_days"),
            update_interval_minutes=defaults.get("update_interval_minutes"),
            strategy_name="none",
            strategy_params=None
        )

        if success:
            logger.info(f"✅ Успешно добавлен {t}/{tf}")
            return HTMLResponse(
                content=f"<script>alert('✅ {t}/{tf} добавлен');location.href='/';</script>"
            )
        else:
            logger.error(f"❌ upsert_instrument_config вернул False для {t}/{tf}")
            return HTMLResponse(
                content="<script>alert('❌ Ошибка добавления (см. лог)');location.href='/';</script>",
                status_code=500
            )
    except Exception as e:
        logger.error(f"💥 Исключение при добавлении {t}/{tf}: {e}", exc_info=True)
        return HTMLResponse(
            content=f"<script>alert('💥 {e}');location.href='/';</script>",
            status_code=500
        )


@router.post("/toggle_tf")
async def toggle_timeframe(
        t: str = Form(...),
        tf: str = Form(...),
        enabled: int = Form(1),
        user: str = Depends(check_auth),
        db=Depends(get_db)
):
    """AJAX-эндпоинт для переключения enabled без перезагрузки."""
    success = toggle_instrument_enabled(db, t, tf, bool(enabled))
    status = "включён" if enabled else "выключен"
    logger.info(f"🔄 {t}/{tf}: {status}")
    return {"ok": success, "ticker": t, "timeframe": tf, "enabled": bool(enabled)}


@router.post("/delete_ticker")
async def delete_ticker(
        t: str,
        user: str = Depends(check_auth),
        db=Depends(get_db)
):
    """🔥 ФИЗИЧЕСКОЕ УДАЛЕНИЕ: удаляет все конфиги и сигналы по тикеру."""
    ticker = t.strip().upper()
    logger.warning(f"🗑️ ЗАПРОС НА УДАЛЕНИЕ: {ticker} (user={user})")

    try:
        deleted_count = delete_instrument_configs_by_ticker(db, ticker)
        logger.info(f"✅ Удалено {ticker}: {deleted_count} записей из instrument_config")

        if deleted_count > 0:
            msg = f"✅ {ticker}: удалено {deleted_count} таймфреймов"
        else:
            msg = f"ℹ️ {ticker}: не найдено активных записей"

        return HTMLResponse(
            content=f"<script>alert('{msg}');location.href='/';</script>"
        )

    except Exception as e:
        logger.error(f"💥 Ошибка удаления {ticker}: {e}", exc_info=True)
        return HTMLResponse(
            content=f"<script>alert('❌ Ошибка: {e}');location.href='/';</script>",
            status_code=500
        )


@router.post("/save_settings")
async def save_instrument_settings(
        request: Request,
        user: str = Depends(check_auth),
        db=Depends(get_db)
):
    """Сохраняет настройки history_depth_days и update_interval_minutes."""
    try:
        form = await request.form()
        ticker = form.get("ticker")
        timeframe = form.get("timeframe")

        if not ticker or not timeframe:
            return {"ok": False, "error": "Missing ticker or timeframe"}

        new_hist = form.get("history_depth_days")
        new_int = form.get("update_interval_minutes")

        history_depth = int(new_hist) if new_hist and new_hist.isdigit() else None
        update_interval = int(new_int) if new_int and new_int.isdigit() else None

        current = db.get_instrument_config(ticker, timeframe)
        if not current:
            return {"ok": False, "error": "Config not found"}

        success = upsert_instrument_config(
            db=db,
            ticker=ticker,
            timeframe=timeframe,
            enabled=current.get("enabled", True),
            history_depth_days=history_depth,
            update_interval_minutes=update_interval,
            strategy_name=current.get("strategy_name", "none"),
            strategy_window=current.get("strategy_window"),
            strategy_params=current.get("strategy_params")
        )

        if success:
            logger.info(f"✅ {ticker}/{timeframe}: settings updated (hist={history_depth}, int={update_interval})")
            return {"ok": True, "ticker": ticker, "timeframe": timeframe}
        else:
            return {"ok": False, "error": "Database error"}

    except Exception as e:
        logger.error(f"❌ Error saving settings: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}