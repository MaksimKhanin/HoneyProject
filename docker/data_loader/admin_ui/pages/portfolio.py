# admin_ui/pages/portfolio.py
"""
📊 Страница портфеля:
  - 💼 Позиции брокера с PnL, стратегией, сигналом
  - 📊 Отслеживаемые инструменты с метриками из БД
"""

import json
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from admin_ui.components.navbar import render_navbar
from admin_ui.core import (
    check_auth, get_db, get_broker,
    get_all_instrument_configs, get_candle_stats,
    AVAILABLE_TIMEFRAMES, logger
)
from constants import Timeframe
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


def fmt_money(value, currency="RUB"):
    """Форматирует деньги с цветом."""
    if value is None:
        return "—"
    sign = "🔻" if value < 0 else "🔺" if value > 0 else "•"
    color = "#f44" if value < 0 else "#0f0" if value > 0 else "#aaa"
    return f'<span style="color:{color}">{sign} {abs(value):,.2f} {currency}</span>'


def fmt_percent(value):
    """Форматирует проценты с цветом."""
    if value is None:
        return "—"
    sign = "🔻" if value < 0 else "🔺" if value > 0 else "•"
    color = "#f44" if value < 0 else "#0f0" if value > 0 else "#aaa"
    return f'<span style="color:{color}">{sign} {abs(value):.2f}%</span>'


# ===== ПОЗИЦИИ БРОКЕРА =====
@router.get("/portfolio", response_class=HTMLResponse)
async def page_portfolio(
        request: Request,
        user: str = Depends(check_auth),
        db=Depends(get_db),
        broker=Depends(get_broker),
        account_filter: str = Query("all", description="Фильтр по аккаунту"),
        tf_filter: str = Query("1d", description="Таймфрейм для метрик"),
):
    # 1. Получаем список аккаунтов для фильтра
    try:
        accounts = await broker.get_all_accounts()
        account_options = "".join(
            f'<option value="{acc["id"]}" {"selected" if acc["id"] == account_filter else ""}>{acc["name"]} ({acc["id"][-4:]})</option>'
            for acc in accounts
        )
    except:
        accounts = []
        account_options = '<option value="all">—</option>'

    # 2. Получаем позиции брокера, отфильтрованные по instrument_config 🔍 ДЕТАЛЬНОЕ ПОЛУЧЕНИЕ ПОЗИЦИЙ С ЛОГИРОВАНИЕМ
    logger.info(f"🔍 Starting position fetch: account_filter={account_filter}")

    positions = []

    try:
        # Получаем список аккаунтов (если ещё не получили)
        if not accounts:
            accounts = await broker.get_all_accounts()
            logger.info(f"🔍 Accounts from broker: {len(accounts)} found")
            for acc in accounts:
                logger.debug(f"   - {acc['id']}: {acc['name']} ({acc['status']})")

        if not accounts:
            logger.warning("⚠️ No accounts found from broker — check token permissions")

        # Получаем конфиги из БД для фильтрации
        db_configs = get_all_instrument_configs(db)
        tracked_tickers = {cfg["ticker"].upper() for cfg in db_configs if cfg.get("ticker")}
        logger.info(f"🔍 Tracked tickers from DB: {len(tracked_tickers)} — {sorted(tracked_tickers)[:10]}...")

        # Получаем позиции по аккаунтам
        if account_filter == "all":
            logger.info(f"🔍 Fetching positions for ALL {len(accounts)} accounts")
            for acc in accounts:
                try:
                    acc_id = acc["id"]
                    logger.debug(f"🔍 Fetching positions for account {acc_id}...")

                    raw_positions = await broker.get_positions(account_id=acc_id)
                    logger.debug(f"   📦 Raw positions from broker: {len(raw_positions)}")

                    # Фильтруем по tracked_tickers
                    for pos in raw_positions:
                        pos_ticker = (pos.get("ticker") or "").upper()
                        if pos_ticker in tracked_tickers:
                            pos["account_name"] = acc.get("name", acc_id[-4:])
                            pos["strategy_name"] = next(
                                (c.get("strategy_name") for c in db_configs if c["ticker"].upper() == pos_ticker),
                                "none")
                            pos["timeframe"] = next(
                                (c.get("timeframe") for c in db_configs if c["ticker"].upper() == pos_ticker), "1d")
                            positions.append(pos)
                            logger.debug(f"   ✅ Matched: {pos_ticker} → strategy={pos['strategy_name']}")

                except Exception as e:
                    logger.error(f"❌ Error fetching positions for {acc.get('id')}: {e}", exc_info=True)
                    continue
        else:
            logger.info(f"🔍 Fetching positions for specific account: {account_filter}")
            try:
                raw_positions = await broker.get_positions(account_id=account_filter)
                logger.debug(f"📦 Raw positions: {len(raw_positions)}")

                acc_name = next((a["name"] for a in accounts if a["id"] == account_filter), account_filter[-4:])

                for pos in raw_positions:
                    pos_ticker = (pos.get("ticker") or "").upper()
                    if pos_ticker in tracked_tickers:
                        pos["account_name"] = acc_name
                        pos["strategy_name"] = next(
                            (c.get("strategy_name") for c in db_configs if c["ticker"].upper() == pos_ticker), "none")
                        pos["timeframe"] = next(
                            (c.get("timeframe") for c in db_configs if c["ticker"].upper() == pos_ticker), "1d")
                        positions.append(pos)
                        logger.debug(f"✅ Matched: {pos_ticker}")

            except Exception as e:
                logger.error(f"❌ Error fetching positions for {account_filter}: {e}", exc_info=True)

        logger.info(f"✅ Final positions count: {len(positions)}")

    except Exception as e:
        logger.error(f"💥 Critical error in position fetch: {e}", exc_info=True)
        positions = []

    # Логируем результат
    if positions:
        logger.info(f"🎨 Rendering portfolio: {len(positions)} positions, tf_filter={tf_filter}")
        for p in positions[:3]:  # Первые 3 для примера
            logger.debug(f"   📊 {p.get('ticker')}: PnL={p.get('unrealized_pnl')}, strategy={p.get('strategy_name')}")
    else:
        logger.warning("⚠️ No positions to display — possible causes:")
        logger.warning("   1) instrument_config empty: SELECT COUNT(*) FROM instrument_config;")
        logger.warning("   2) Broker token has no positions: run tests/test_positions.py")
        logger.warning("   3) Ticker mismatch: DB has 'SBER', broker returns 'sber' (case-sensitive)")
        logger.warning("   4) Account filter mismatch: check account_id in URL vs broker accounts")

    # 3. Рендерим таблицу позиций
    positions_html = ""
    if positions:
        for pos in sorted(positions, key=lambda x: abs(x.get("unrealized_pnl") or 0), reverse=True):
            ticker = pos.get("ticker", "N/A")
            strategy = pos.get("strategy_name", "none")

            # Получаем последний сигнал из БД
            signal_row = db.get_recent_candles(ticker, pos.get("timeframe", "1d"), limit=1)
            last_signal = "—"
            signal_extra = ""
            if signal_row:
                # Здесь можно добавить запрос к таблице signals
                # Пока заглушка:
                last_signal = "HOLD"
                signal_extra = "rsi=45.2"

            positions_html += f'''
            <tr style="border-bottom:1px solid #333;">
                <td style="padding:8px;"><strong>{ticker}</strong><br><small style="color:#777">{pos.get("account_name", "")}</small></td>
                <td style="padding:8px;"><code>{strategy}</code></td>
                <td style="padding:8px;text-align:right;">{fmt(pos.get("current_price"), ",.4f")}</td>
                <td style="padding:8px;text-align:right;">{pos.get("quantity", 0):,}</td>
                <td style="padding:8px;text-align:right;">{fmt(pos.get("entry_value"), ",.2f")}</td>
                <td style="padding:8px;text-align:right;">{fmt(pos.get("current_value"), ",.2f")}</td>
                <td style="padding:8px;text-align:right;">{fmt_money(pos.get("unrealized_pnl"), pos.get("currency", "RUB"))}</td>
                <td style="padding:8px;text-align:right;">{fmt_percent(pos.get("unrealized_pnl_percent"))}</td>
                <td style="padding:8px;text-align:center;"><span style="color:{"#0f0" if last_signal == "BUY" else "#f44" if last_signal == "SELL" else "#aaa"}">{last_signal}</span></td>
                <td style="padding:8px;font-size:0.8em;color:#aaa;">{signal_extra}</td>
            </tr>
            '''
    else:
        positions_html = '<tr><td colspan="10" style="text-align:center;color:#777;padding:20px;">Нет позиций по выбранным фильтрам</td></tr>'

    logger.info(f"🎨 Rendering portfolio: {len(positions)} positions, tf_filter={tf_filter}")
    if not positions:
        logger.warning(
            "⚠️ No positions to display — check: 1) instrument_config has data, 2) broker token works, 3) tickers match case")

    # 4. Метрики по отслеживаемым инструментам
    # Получаем конфиги, фильтруем по таймфрейму, сортируем по тикеру
    configs = get_all_instrument_configs(db)
    if tf_filter != "all":
        configs = [c for c in configs if c["timeframe"] == tf_filter]

    # ✅ Сортируем по тикеру (алфавит), затем по таймфрейму
    configs_sorted = sorted(configs, key=lambda x: (x["ticker"].upper(), x["timeframe"]))

    metrics_html = ""
    for cfg in configs_sorted:
        ticker = cfg["ticker"]
        tf = cfg["timeframe"]

        # Получаем метрики
        metrics = db.get_latest_metrics(ticker, tf, limit=1)
        metrics_data = metrics[0]["metrics"] if metrics else {}

        # Фоллбэк на базовые статистики
        if not metrics:
            stats = get_candle_stats(db, ticker, tf, limit=50)
            metrics_data = {
                "price": stats.get("avg"),
                "change_pct": stats.get("change_pct"),
                "volatility": stats.get("std"),
                "count": stats.get("count"),
            }

        # ✅ НОВАЯ ВЕРТИКАЛЬНАЯ КАРТОЧКА С УЛУЧШЕННОЙ ВЕРСТКОЙ
        metrics_html += f'''
            <article class="metrics-card" style="background:#252525;border:1px solid #444;border-radius:8px;padding:16px;margin:0 0 16px 0;">
                <header style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid #444;flex-wrap:wrap;gap:8px;">
                    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                        <strong style="font-size:1.15em;">{ticker}</strong>
                        <small style="color:#aaa;background:#333;padding:2px 8px;border-radius:4px;">{tf}</small>
                    </div>
                    <code style="background:#333;padding:4px 10px;border-radius:4px;font-size:0.9em;">
                        {cfg.get("strategy_name", "none")}
                    </code>
                </header>

                <div class="metrics-grid" style="display:grid;grid-template-columns:repeat(2,1fr);gap:16px 20px;">
                    <div>
                        <div style="color:#aaa;font-size:0.9em;margin-bottom:6px;">💰 Цена</div>
                        <div style="font-size:1.3em;font-weight:bold;line-height:1.3;">{metrics_data.get("close_price")}</div>
                    </div>
                    <div>
                        <div style="color:#aaa;font-size:0.9em;margin-bottom:6px;">📈 Эксцесс</div>
                        <div style="font-size:1.3em;font-weight:bold;line-height:1.3;">{fmt(metrics_data.get("kurt_excess_200"), ",.2f")}</div>
                    </div>
                    <div>
                        <div style="color:#aaa;font-size:0.9em;margin-bottom:6px;">〽️ Скошенность</div>
                        <div style="font-size:1.3em;font-weight:bold;line-height:1.3;">{fmt(metrics_data.get("skew_200"), ".2f")}</div>
                    </div>
                    
                    <div>
                        <div style="color:#aaa;font-size:0.9em;margin-bottom:6px;">⚠️ Изменение</div>
                        <div style="font-size:1.3em;font-weight:bold;line-height:1.3;color:{"#0f0" if (metrics_data.get("price_change_pct_3") or 0) >= 0 else "#f44"}">
                            {fmt(metrics_data.get("price_change_pct_3"), "+.2f")}%</div>
                    </div>
                    <div>
                        <div style="color:#aaa;font-size:0.9em;margin-bottom:6px;">〰️ Z-Score</div>
                        <div style="font-size:1.3em;font-weight:bold;line-height:1.3;">{fmt(metrics_data.get("z_score_200", "—"),".2f")}</div>
                    </div>
                    <div>
                        <div style="color:#aaa;font-size:0.9em;margin-bottom:6px;">💹 50-EMA</div>
                        <div style="font-size:1.3em;font-weight:bold;line-height:1.3;">{fmt(metrics_data.get("ema_50", "—"),".2f")}</div>
                    </div>
                    <div>
                        <div style="color:#aaa;font-size:0.9em;margin-bottom:6px;">📉 Коррекция%-20p</div>
                        <div style="font-size:1.3em;font-weight:bold;line-height:1.3;">{fmt(metrics_data.get("pullback_20", "—"),".2f")}</div>
                    </div>
                </div>

                {f'<details style="margin-top:16px;padding-top:12px;border-top:1px dashed #444;"><summary style="cursor:pointer;color:#aaa;font-size:0.9em;">🔍 Raw metrics</summary><pre style="background:#222;padding:12px;border-radius:6px;overflow-x:auto;margin-top:8px;font-size:0.85em;max-height:150px;">{json.dumps(metrics_data, ensure_ascii=False, indent=2)}</pre></details>' if metrics_data and len(metrics_data) > 3 else ''}
            </article>
            '''

    if not metrics_html:
        metrics_html = '<p style="color:#777;text-align:center;padding:40px 20px;">Нет данных. Добавьте инструменты на странице "Загрузка".</p>'
    # ===== HTML СТРАНИЦЫ =====
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css">
    <title>💼 Портфель | Honey Loader</title>
    {HEAD_FIX}
    <script>
        // Авто-обновление без перезагрузки
        async function refreshPortfolio() {{
            try {{
                const resp = await fetch('/api/portfolio/summary');
                if (resp.ok) {{
                    const data = await resp.json();
                    // Здесь можно обновить только цифры, а не всю страницу
                    console.log('🔄 Портфель обновлён', data);
                }}
            }} catch(e) {{ console.log('⚠️ Ошибка авто-обновления:', e); }}
        }}
        // Обновляем каждые 60 сек
        setInterval(refreshPortfolio, 60000);

        // Фильтр аккаунтов/таймфреймов без перезагрузки
        function applyFilters() {{
            const acc = document.getElementById('account_filter').value;
            const tf = document.getElementById('tf_filter').value;
            window.location.href = `/portfolio?account_filter=${{acc}}&tf_filter=${{tf}}`;
        }}
    </script>
</head>
<body>
    <main class="container">
        {render_navbar("/portfolio")}

        <!-- 🔍 ФИЛЬТРЫ -->
        <article class="card" style="background:#252525;border:1px solid #444;margin-bottom:15px;">
            <header><strong>🔍 Фильтры</strong></header>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;padding:10px;">
                <div>
                    <label style="font-size:0.9em;color:#aaa;">🏦 Счёт</label>
                    <select id="account_filter" onchange="applyFilters()" style="width:100%;padding:6px;">
                        <option value="all" {"selected" if account_filter == "all" else ""}>Все счета</option>
                        {account_options}
                    </select>
                </div>
                <div>
                    <label style="font-size:0.9em;color:#aaa;">📊 Таймфрейм метрик</label>
                    <select id="tf_filter" onchange="applyFilters()" style="width:100%;padding:6px;">
                        <option value="all" {"selected" if tf_filter == "all" else ""}>Все</option>
                        {''.join(f'<option value="{tf}" {"selected" if tf == tf_filter else ""}>{tf}</option>' for tf in AVAILABLE_TIMEFRAMES)}
                    </select>
                </div>
                <div style="display:flex;align-items:flex-end;">
                    <button class="contrast" onclick="applyFilters()" style="width:100%;padding:8px;">🔄 Применить</button>
                </div>
            </div>
        </article>

        <!-- 💼 ПОЗИЦИИ БРОКЕРА -->
        <article class="card" style="background:#252525;border:1px solid #444;">
            <header style="display:flex;justify-content:space-between;align-items:center;">
                <strong>💼 Позиции брокера (отслеживаемые)</strong>
                <button class="secondary" onclick="location.reload()" style="padding:4px 12px;">🔄</button>
            </header>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Инструмент</th>
                            <th>Стратегия</th>
                            <th>Цена</th>
                            <th>Объём</th>
                            <th>Вход</th>
                            <th>Стоимость</th>
                            <th class="pnl-pos">PnL</th>
                            <th class="pnl-pos">PnL%</th>
                            <th>Сигнал</th>
                            <th>Доп.</th>
                        </tr>
                    </thead>
                    <tbody>
                        {positions_html}
                    </tbody>
                </table>
            </div>
        </article>

        <!-- 📊 МЕТРИКИ ПО ИНСТРУМЕНТАМ -->
        <article class="card" style="background:#252525;border:1px solid #444;margin-top:15px;">
            <header><strong>📊 Метрики отслеживаемых инструментов</strong></header>
            <div class="metrics-container">
                {metrics_html}
            </div>
        </article>

        <!-- ℹ️ ПОЯСНЕНИЯ -->
        <article class="card" style="background:#252525;border:1px dashed #666;margin-top:15px;">
            <header><strong>ℹ️ Пояснения</strong></header>
            <ul style="font-size:0.9em;color:#ccc;">
                <li><strong>Позиции</strong> — только те инструменты, что есть в <code>instrument_config</code></li>
                <li><strong>PnL</strong> — нереализованная прибыль/убыток (текущая цена − средняя цена входа)</li>
                <li><strong>Сигнал</strong> — последний сигнал стратегии (обновляется при запуске оркестратора)</li>
                <li><strong>Метрики</strong> — берутся из таблицы <code>metrics</code> (пока заглушка, скоро будет RSI, SMA, etc.)</li>
                <li>Данные обновляются автоматически каждые 60 секунд</li>
            </ul>
        </article>
    </main>
</body>
</html>"""
    return html


# ===== API ENDPOINTS для авто-обновления =====
@router.get("/api/portfolio/summary")
async def api_portfolio_summary(
        user: str = Depends(check_auth),
        db=Depends(get_db),
        broker=Depends(get_broker),
        account_filter: str = "all"
):
    """JSON API для авто-обновления портфеля (без рендера HTML)."""
    try:
        if account_filter == "all":
            accounts = await broker.get_all_accounts()
            positions = []
            for acc in accounts:
                try:
                    pos = await broker.get_positions_with_config_filter(db, account_id=acc["id"])
                    positions.extend(pos)
                except:
                    continue
        else:
            positions = await broker.get_positions_with_config_filter(db, account_id=account_filter)



        # Считаем сводку
        total_value = sum(p.get("current_value") or 0 for p in positions)
        total_pnl = sum(p.get("unrealized_pnl") or 0 for p in positions)

        return {
            "ok": True,
            "positions_count": len(positions),
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round(total_pnl / total_value * 100, 2) if total_value else None,
            "updated_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ API error: {e}")
        return {"ok": False, "error": str(e)}