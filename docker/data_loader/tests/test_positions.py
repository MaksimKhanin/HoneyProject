#!/usr/bin/env python3
# tests/test_positions.py
"""
🧪 Тестовый скрипт для проверки получения позиций и PnL из Tinkoff API.

Запуск:
    python tests/test_positions.py

Требования:
    - Установленная переменная TINKOFF_TOKEN
    - Доступ к API Tinkoff Invest
"""

import os
import sys
import asyncio
from pathlib import Path
import argparse

# Добавляем корень проекта в path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from pathlib import Path


project_root = Path(__file__).parent.parent.parent.parent
print(project_root)

load_dotenv(project_root / ".env")

print(f"DB_HOST: {os.getenv('DB_HOST', 'НЕ ЗАГРУЖЕН')}")
print(f"TINKOFF_TOKEN: {'***' if os.getenv('TINKOFF_TOKEN') else 'НЕ ЗАГРУЖЕН'}")

from T_con import TConnector
from constants import DEFAULT_LOG_LEVEL


def fmt_money(value, currency="RUB"):
    """Форматирует деньги с разделителями."""
    if value is None:
        return "—"
    sign = "🔻" if value < 0 else "🔺" if value > 0 else "•"
    color = "\033[91m" if value < 0 else "\033[92m" if value > 0 else "\033[93m"
    reset = "\033[0m"
    return f"{color}{sign} {abs(value):,.2f} {currency}{reset}"


def fmt_percent(value):
    """Форматирует проценты с цветом."""
    if value is None:
        return "—"
    sign = "🔻" if value < 0 else "🔺" if value > 0 else "•"
    color = "\033[91m" if value < 0 else "\033[92m" if value > 0 else "\033[93m"
    reset = "\033[0m"
    return f"{color}{sign} {value:+.2f}%{reset}"

def fmt_datetime(dt):
    """Безопасное форматирование времени."""
    if not dt:
        return "—"
    if hasattr(dt, 'strftime'):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(dt)


# ===== ОСНОВНАЯ ЛОГИКА =====

async def show_accounts(connector: TConnector):
    """Показывает список всех аккаунтов."""
    print("\n📋 ДОСТУПНЫЕ АККАУНТЫ")
    print("=" * 100)

    accounts = await connector.get_all_accounts()
    if not accounts:
        print("❌ Аккаунты не найдены")
        return

    print(f"{'ID':<20} {'Имя':<25} {'Тип':<12} {'Статус':<22} {'Валюта':<8} {'Открыт'}")
    print("-" * 100)

    for acc in accounts:
        status_emoji = "🟢" if acc["status"] == "ACCOUNT_STATUS_OPEN" else "🔴"
        opened = acc["opened_date"].strftime("%Y-%m-%d") if acc.get("opened_date") else "—"
        print(
            f"{acc['id']:<20} "
            f"{acc['name']:<25} "
            f"{acc['account_type']:<12} "
            f"{status_emoji} {acc['status']:<20} "
            f"{acc['currency']:<8} "
            f"{opened}"
        )

    # Подсказка как использовать
    print("\n💡 Чтобы использовать конкретный аккаунт:")
    print(f"   python {Path(__file__).name} --account <ID>")


async def show_portfolio_summary(connector: TConnector, account_id: str = None):
    """Показывает сводку по портфелю с корректной базовой валютой."""
    print(f"\n📊 СВОДКА ПО ПОРТФЕЛЮ{' (' + account_id + ')' if account_id else ''}")
    print("=" * 80)

    summary = await connector.get_portfolio_summary(account_id=account_id)
    cur = summary.get('base_currency', 'RUB')

    print(f"Общая стоимость:     {fmt_money(summary['total_value'], cur)}")
    print(f"Общий PnL:           {fmt_money(summary['total_pnl'], cur)}  ({fmt_percent(summary['total_pnl_percent'])})")
    print(
        f"Позиций всего:       {summary['positions_count']} (Long: {summary['long_positions']}, Short: {summary['short_positions']})")
    print(f"Валюты в портфеле:   {', '.join(summary['currencies']) or '—'}")
    print(f"Обновлено:           {fmt_datetime(summary['updated_at'])}")


async def show_all_positions(connector: TConnector, account_id: str = None):
    """Показывает все открытые позиции с безопасным форматированием."""
    print(f"\n📋 ВСЕ ОТКРЫТЫЕ ПОЗИЦИИ{' (' + account_id + ')' if account_id else ''}")
    print("=" * 130)
    print(f"{'Тикер':<12} {'Тип':<8} {'Кол-во':>8} {'Вход':>12} {'Текущая':>12} {'PnL':>16} {'PnL%':>8} {'Валюта':<6}")
    print("-" * 130)

    positions = await connector.get_positions(account_id=account_id)
    if not positions:
        print("ℹ️ Нет открытых позиций")
        return

    for pos in sorted(positions, key=lambda x: abs(x.get("unrealized_pnl") or 0), reverse=True):
        ticker = str(pos.get("ticker", "N/A"))[:12]
        ptype = str(pos.get("instrument_type", "?"))[:8]
        qty = pos.get("quantity", 0)

        # ✅ ИСПОЛЬЗУЕМ АКТУАЛЬНЫЕ КЛЮЧИ ИЗ TCONNECTOR
        entry = pos.get("average_position_price")
        current = pos.get("current_price")
        pnl = pos.get("unrealized_pnl")
        pnl_pct = pos.get("unrealized_pnl_percent")
        currency = pos.get("currency", "RUB")

        # ✅ БЕЗОПАСНОЕ ФОРМАТИРОВАНИЕ (None → "—")
        entry_str = f"{entry:,.4f}" if entry is not None else "—"
        curr_str = f"{current:,.4f}" if current is not None else "—"

        print(
            f"{ticker:<12} "
            f"{ptype:<8} "
            f"{qty:>8,} "
            f"{entry_str:>12} "
            f"{curr_str:>12} "
            f"{fmt_money(pnl, currency):>16} "
            f"{fmt_percent(pnl_pct):>8} "
            f"{currency:<6}"
        )

    total_pnl = sum(p.get("unrealized_pnl") or 0 for p in positions)
    print("-" * 130)
    print(f"{'ИТОГО PnL:':>100} {fmt_money(total_pnl, positions[0].get('currency', 'RUB'))}")

async def show_filtered_positions(connector: TConnector, db, account_id: str = None):
    """Показывает только позиции, которые есть в instrument_config."""
    print(f"\n🔍 ПОЗИЦИИ, ОТслеживаемые В СИСТЕМЕ{' (' + account_id + ')' if account_id else ''}")
    print("=" * 120)
    print(f"{'Тикер':<10} {'Таймфрейм':<10} {'Стратегия':<15} {'Кол-во':>8} {'PnL':>18} {'PnL%':>10} {'Валюта':<6}")
    print("-" * 120)

    filtered = await connector.get_positions_with_config_filter(db, account_id=account_id)

    if not filtered:
        print("ℹ️ Нет отслеживаемых позиций")
        print("💡 Добавь инструменты через UI или напрямую в БД:")
        print("   INSERT INTO instrument_config (ticker, timeframe, strategy_name) VALUES ('SBER', '1d', 'sma_cross');")
        return

    for pos in filtered:
        ticker = (pos.get("ticker") or "N/A")[:10]

        # Получаем конфиг из БД (берём первый активный таймфрейм)
        cfg = db.get_instrument_config(ticker, "1d")  # дефолт 1d
        if not cfg:
            # Пробуем найти любой конфиг по тикеру
            all_cfgs = [c for c in db.get_all_instrument_configs() if c["ticker"].upper() == ticker.upper()]
            cfg = all_cfgs[0] if all_cfgs else None

        tf = cfg.get("timeframe", "—") if cfg else "—"
        strat = cfg.get("strategy_name", "none") if cfg else "—"

        qty = pos.get("quantity", 0)
        pnl = pos.get("unrealized_pnl")
        pnl_pct = pos.get("unrealized_pnl_percent")
        currency = pos.get("currency", "RUB")

        print(
            f"{ticker:<10} "
            f"{tf:<10} "
            f"{strat:<15} "
            f"{qty:>8,} "
            f"{fmt_money(pnl, currency):>18} "
            f"{fmt_percent(pnl_pct):>10} "
            f"{currency:<6}"
        )


# ===== ОБНОВЛЁННЫЙ MAIN С ЦИКЛОМ ПО АККАУНТАМ =====
async def main():
    parser = argparse.ArgumentParser(description="🧪 Тест позиций Tinkoff API")
    parser.add_argument("--account", type=str, help="ID конкретного аккаунта")
    parser.add_argument("--all-accounts", action="store_true", help="Показать данные по ВСЕМ доступным аккаунтам")
    parser.add_argument("--list-accounts", action="store_true", help="Только список аккаунтов")
    parser.add_argument("--filtered", action="store_true", help="Только позиции из instrument_config")
    args = parser.parse_args()

    print("🔥 Тест позиций Tinkoff API\n" + "=" * 80)
    token = os.getenv("TINKOFF_TOKEN")
    if not token or token in ("YOUR_TOKEN_HERE", "xxx", ""):
        print("❌ TINKOFF_TOKEN не установлен!");
        sys.exit(1)

    connector = TConnector(token=token, log_level="WARNING")
    try:
        if args.list_accounts:
            await show_accounts(connector);
            return

        # Определяем список аккаунтов для обработки
        if args.account:
            target_accounts = [{"id": args.account, "name": "Указанный вручную"}]
        else:
            target_accounts = await connector.get_all_accounts()
            if not target_accounts: print("❌ Аккаунты не найдены"); return

        print(f"📋 Найдено аккаунтов: {len(target_accounts)}")

        for acc in target_accounts:
            acc_id = acc["id"]
            print(f"\n{'─' * 40} АККАУНТ: {acc_id} ({acc.get('name', '')}) {'─' * 40}")

            # Сбрасываем кэш, чтобы каждый запрос шёл явно на нужный аккаунт
            connector._account_id = None

            try:
                await show_portfolio_summary(connector, acc_id)
                if not args.filtered:
                    await show_all_positions(connector, acc_id)
                else:
                    # Здесь можно добавить вывод filtered позиций, если нужно
                    pass
            except Exception as e:
                print(f"⚠️ Ошибка обработки аккаунта {acc_id}: {e}")

        print("\n✅ Тест завершён")
    finally:
        await connector.close()


if __name__ == "__main__":
    asyncio.run(main())