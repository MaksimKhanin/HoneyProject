# admin_ui/pages/signals.py
"""
📡 Страница сигналов:
  - 📊 Таблица последних актуальных сигналов от стратегий
  - 🕐 Дата и время сигнала, тикер, стратегия, сигнал, цена и метаданные
"""

from datetime import datetime
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from admin_ui.components.navbar import render_navbar
from admin_ui.core import check_auth, get_db, logger
from .common_lib import HEAD_FIX

router = APIRouter()


# ===== ФОРМАТТИРОВАНИЕ =====
def fmt(value, spec=".2f"):
    """Безопасное форматирование чисел."""
    if value is None:
        return "—"
    try:
        return f"{float(value):{spec}}"
    except (ValueError, TypeError):
        return str(value)


def fmt_datetime(dt):
    """Форматирует дату и время."""
    if dt is None:
        return "—"
    try:
        if isinstance(dt, str):
            return dt
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(dt)


def get_signal_color(signal):
    """Возвращает цвет для сигнала."""
    if signal == "BUY":
        return "#0f0"
    elif signal == "SELL":
        return "#f44"
    elif signal == "HOLD":
        return "#aaa"
    elif signal in ("CLOSE_BUY", "CLOSE_SELL", "CLOSE_ALL"):
        return "#ff0"
    else:
        return "#fff"


def get_signal_emoji(signal):
    """Возвращает эмодзи для сигнала."""
    emoji_map = {
        "BUY": "🟢",
        "SELL": "🔴",
        "HOLD": "🟡",
        "CLOSE_BUY": "🔵",
        "CLOSE_SELL": "🟣",
        "CLOSE_ALL": "⚫",
        "ERROR": "⚪"
    }
    return emoji_map.get(signal, "⚪")


@router.get("/signals", response_class=HTMLResponse)
async def page_signals(
        request: Request,
        user: str = Depends(check_auth),
        db=Depends(get_db),
        limit: int = Query(100, description="Максимум сигналов"),
        ticker_filter: str = Query("all", description="Фильтр по тикуру"),
):
    """Страница последних сигналов."""

    # Получаем уникальные тикеры для фильтра
    all_tickers = set()
    signals = []

    try:
        # Получаем последние сигналы из БД
        signals = db.get_recent_signals(limit=limit)
        logger.info(f"📡 Получено {len(signals)} сигналов")

        # Собираем уникальные тикеры
        for sig in signals:
            ticker = sig.get("ticker", "")
            if ticker:
                all_tickers.add(ticker.upper())

    except Exception as e:
        logger.error(f"❌ Ошибка получения сигналов: {e}", exc_info=True)
        signals = []

    # Фильтр по тикуру
    if ticker_filter != "all":
        signals = [s for s in signals if s.get("ticker", "").upper() == ticker_filter.upper()]

    # Опции для фильтра тикеров
    ticker_options = f'<option value="all" {"selected" if ticker_filter == "all" else ""}>Все тикеры</option>'
    for t in sorted(all_tickers):
        ticker_options += f'<option value="{t}" {"selected" if t == ticker_filter else ""}>{t}</option>'

    # Рендерим таблицу сигналов
    signals_html = ""
    if signals:
        # Сортируем сигналы по candle_time (от новых к старым)
        def get_candle_time(sig):
            ct = sig.get("candle_time")
            if ct is None:
                return datetime.min
            if isinstance(ct, str):
                try:
                    return datetime.fromisoformat(ct.replace("Z", "+00:00"))
                except:
                    return datetime.min
            return ct

        signals_sorted = sorted(signals, key=get_candle_time, reverse=True)

        # Оставляем только последний сигнал по каждому инструменту (ticker + strategy)
        latest_signals = {}
        for sig in signals_sorted:
            key = (sig.get("ticker", ""), sig.get("strategy", ""))
            if key not in latest_signals:  # Берём первый (самый свежий) для каждой пары
                latest_signals[key] = sig

        # Преобразуем обратно в список
        signals = list(latest_signals.values())

        for sig in signals:
            ticker = sig.get("ticker", "N/A")
            timeframe = sig.get("timeframe", "N/A")
            strategy = sig.get("strategy", "none")
            signal = sig.get("signal", "UNKNOWN")
            price = sig.get("price", 0)
            candle_time = sig.get("candle_time")
            created_at = sig.get("created_at")
            metadata = sig.get("metadata", {})

            # Парсим metadata если это строка
            if isinstance(metadata, str):
                import json
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}

            signal_color = get_signal_color(signal)
            signal_emoji = get_signal_emoji(signal)

            # Формируем полный JSON для метаданных
            import json
            metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2) if metadata else "{}"

            # Уникальный ID для спойлера
            spoiler_id = f"meta_{ticker}_{strategy}".replace("-", "_").replace(".", "_").replace(" ", "_")

            signals_html += f'''
            <tr style="border-bottom:1px solid #333;">
                <td style="padding:8px;"><strong>{ticker}</strong><br><small style="color:#777">{timeframe}</small></td>
                <td style="padding:8px;"><code style="font-size:0.85em;">{strategy}</code></td>
                <td style="padding:8px;text-align:center;">
                    <span style="color:{signal_color};font-weight:bold;">{signal_emoji} {signal}</span>
                </td>
                <td style="padding:8px;text-align:right;">{fmt(price, ",.4f")}</td>
                <td style="padding:8px;text-align:center;">{fmt_datetime(candle_time)}</td>
                <td style="padding:8px;text-align:center;">{fmt_datetime(created_at)}</td>
                <td style="padding:8px;font-size:0.8em;">
                    <details style="cursor:pointer;">
                        <summary style="color:#aaa;font-size:0.85em;">📄 Показать метаданные</summary>
                        <pre style="background:#1a1a1a;padding:8px;border-radius:4px;overflow-x:auto;font-size:0.75em;color:#0f0;margin-top:5px;">{metadata_json}</pre>
                    </details>
                </td>
            </tr>
            '''
    else:
        signals_html = '<tr><td colspan="7" style="text-align:center;color:#777;padding:20px;">Нет сигналов за выбранный период</td></tr>'

    # ===== HTML СТРАНИЦЫ =====
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css">
    <title>📡 Сигналы | Honey Loader</title>
    {HEAD_FIX}
    <script>
        // Авто-обновление каждые 30 секунд
        setInterval(() => {{
            location.reload();
        }}, 30000);

        // Фильтр тикеров
        function applyFilter() {{
            const ticker = document.getElementById('ticker_filter').value;
            const limit = document.getElementById('limit_filter').value;
            window.location.href = `/signals?ticker_filter=${{ticker}}&limit=${{limit}}`;
        }}
    </script>
</head>
<body>
    <main class="container">
        {render_navbar("/signals")}

        <!-- 🔍 ФИЛЬТРЫ -->
        <article class="card" style="background:#252525;border:1px solid #444;margin-bottom:15px;">
            <header><strong>🔍 Фильтры</strong></header>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;padding:10px;">
                <div>
                    <label style="font-size:0.9em;color:#aaa;">📊 Тикер</label>
                    <select id="ticker_filter" onchange="applyFilter()" style="width:100%;padding:6px;">
                        {ticker_options}
                    </select>
                </div>
                <div>
                    <label style="font-size:0.9em;color:#aaa;">📋 Лимит</label>
                    <select id="limit_filter" onchange="applyFilter()" style="width:100%;padding:6px;">
                        <option value="50" {"selected" if limit == 50 else ""}>50</option>
                        <option value="100" {"selected" if limit == 100 else ""}>100</option>
                        <option value="200" {"selected" if limit == 200 else ""}>200</option>
                        <option value="500" {"selected" if limit == 500 else ""}>500</option>
                    </select>
                </div>
                <div style="display:flex;align-items:flex-end;">
                    <button class="contrast" onclick="applyFilter()" style="width:100%;padding:8px;">🔄 Применить</button>
                </div>
            </div>
        </article>

        <!-- 📡 ТАБЛИЦА СИГНАЛОВ -->
        <article class="card" style="background:#252525;border:1px solid #444;">
            <header style="display:flex;justify-content:space-between;align-items:center;">
                <strong>📡 Последние сигналы стратегий</strong>
                <button class="secondary" onclick="location.reload()" style="padding:4px 12px;">🔄</button>
            </header>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Инструмент</th>
                            <th>Стратегия</th>
                            <th>Сигнал</th>
                            <th>Цена</th>
                            <th>Свеча</th>
                            <th>Обновлено</th>
                            <th>Метаданные</th>
                        </tr>
                    </thead>
                    <tbody>
                        {signals_html}
                    </tbody>
                </table>
            </div>
        </article>

        <!-- ℹ️ ПОЯСНЕНИЯ -->
        <article class="card" style="background:#252525;border:1px dashed #666;margin-top:15px;">
            <header><strong>ℹ️ Пояснения</strong></header>
            <ul style="font-size:0.9em;color:#ccc;">
                <li><strong>Сигналы</strong> — генерируются стратегиями при обработке свечей</li>
                <li><strong>Свеча</strong> — время свечи, по которой рассчитан сигнал</li>
                <li><strong>Обновлено</strong> — время записи сигнала в БД</li>
                <li><strong>Метаданные</strong> — дополнительная информация (режим исполнения, количество свечей и т.д.)</li>
                <li>Данные обновляются автоматически каждые 30 секунд</li>
                <li>Для включения записи сигналов убедитесь, что стратегия активна в <code>instrument_config</code></li>
            </ul>
        </article>
    </main>
</body>
</html>"""
    return html