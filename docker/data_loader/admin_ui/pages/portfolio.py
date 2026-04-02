# admin_ui/pages/portfolio.py
"""Страница портфеля: статистика, метрики, сигналы."""

import math
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from admin_ui.components.navbar import render_navbar
from admin_ui.components.helpers import fmt
from admin_ui.components.theme import render_head
from admin_ui.core import check_auth, logger
from admin_ui.components.helpers import fmt

router = APIRouter()


def calc_basic_stats(prices: list) -> dict:
    """Простые статистики без pandas."""
    if not prices:
        return {"avg": None, "std": None, "min": None, "max": None, "sharpe_approx": None}
    n = len(prices)
    avg = sum(prices) / n
    variance = sum((x - avg) ** 2 for x in prices) / n if n > 1 else 0
    std = math.sqrt(variance)
    if n >= 2 and std > 0:
        returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, n) if prices[i - 1] != 0]
        avg_ret = sum(returns) / len(returns) if returns else 0
        sharpe = avg_ret / std * math.sqrt(252)
    else:
        sharpe = None
    return {"avg": avg, "std": std, "min": min(prices), "max": max(prices), "sharpe_approx": sharpe}


@router.get("/portfolio", response_class=HTMLResponse)
async def page_portfolio(user: str = Depends(check_auth)):
    # 🔥 Заглушка данных (потом заменим на запрос к БД)
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

    # Пример метрик
    sample_prices = [150.1, 151.2, 150.8, 152.0, 152.34]
    stats = calc_basic_stats(sample_prices)

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
                <div style="font-size:1.2em;font-weight:bold;">{fmt(stats["min"])} – {fmt(stats["max"])}</div>
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
    <script>setInterval(() => location.reload(), 60000);</script>
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
                <thead><tr><th>Инструмент</th><th>Стратегия</th><th>Цена</th><th>Сигналы (24ч)</th><th>Последний сигнал</th><th>Время</th></tr></thead>
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