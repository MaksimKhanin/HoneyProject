#!/usr/bin/env python3
"""
🧪 АТОМАРНЫЙ ТЕСТ СТРАТЕГИЙ
Запуск без конфига, без брокера, без MainLoader.
Только: БД → Данные → Стратегия → Результат

Примеры:
  # Простой тест (дефолтные настройки)
  python test_strategy_atomic.py --ticker GAZP --timeframe 1h --strategy rsi_oversold

  # С кастомным окном и выводом данных
  python test_strategy_atomic.py -t VTBR -tf 1d -s sma_cross -w 100 --show-data

  # Тест с подключением к реальной БД (указать параметры)
  python test_strategy_atomic.py -t SBER -tf 1m -s momentum --db-host localhost --db-name tink
"""

import sys
import os
import argparse
import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# 🔥 Добавляем корень проекта в путь (если запускаем не из корня)
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Импорты наших модулей
from strategy import run_strategy, STRATEGY_REGISTRY, STRATEGY_FUNCS, get_price_type


# 🔥 Опционально: если есть db_manager — раскомментируй
from db_manager import DBManager


# === МОК-БАЗА ДАННЫХ (для тестов без реальной БД) ===
class MockDB:
    """Заглушка БД для тестов без подключения."""

    def __init__(self, ticker: str = "TEST", timeframe: str = "1h"):
        self.ticker = ticker
        self.timeframe = timeframe
        self._candles = self._generate_mock_data()

    def _generate_mock_data(self, count: int = 100) -> List[Dict]:
        """Генерирует реалистичные тестовые данные (случайное блуждание)."""
        import random
        random.seed(42)  # Для воспроизводимости

        candles = []
        price = 100.0
        base_time = datetime(2024, 1, 1, 0, 0, 0)

        for i in range(count):
            # Случайное изменение цены ±2%
            change = random.uniform(-0.02, 0.02)
            price = price * (1 + change)

            candles.append({
                'time': base_time + timedelta(hours=i),
                'open': price,
                'high': price * random.uniform(1.0, 1.01),
                'low': price * random.uniform(0.99, 1.0),
                'close': price,
                'volume': random.randint(1000, 100000)
            })
        return candles

    def get_recent_candles(self, ticker: str, timeframe: str, limit: int) -> List[Dict]:
        """Возвращает последние N свечей (из мока)."""
        return self._candles[-limit:] if self._candles else []


# === РЕАЛЬНАЯ БД (если есть db_manager) ===
def get_real_db(config_path: Optional[str] = None):
    """Пытается подключиться к реальной БД. Возвращает None если не вышло."""
    try:
        from db_manager import DBManager
        import yaml

        # Если передан config_path — грузим из него
        if config_path and os.path.exists(config_path):
            db = DBManager(config_path)
            print(f"✅ БД: {config_path}")
            return db
        # Верни обёртку над conn, совместимую с get_recent_candles()

    except Exception as e:
        print(f"⚠️ БД не доступна: {e}")


# === ТЕСТОВЫЙ ЗАПУСКАТОР ===
def run_atomic_test(
        ticker: str,
        timeframe: str,
        strategy_name: str,
        window: Optional[int] = None,
        db=None,
        show_data: bool = False,
        show_debug: bool = False
) -> Dict:
    """
    Атомарный запуск стратегии.

    :return: словарь с результатами теста
    """
    result = {
        'ticker': ticker,
        'timeframe': timeframe,
        'strategy': strategy_name,
        'success': False,
        'error': None,
        'signal': None,
        'data_points': 0,
        'price_last': None,
        'debug': {}
    }

    try:
        # 1. Получаем данные из БД (мока или реальной)
        # if db is None:
        #     db = MockDB(ticker, timeframe)

        # Определяем окно стратегии
        default_windows = {
            "sma_cross": 50, "rsi_oversold": 30,
            "momentum": 10, "bollinger": 40
        }
        effective_window = window or default_windows.get(strategy_name, 20)

        # Запрашиваем данные с запасом
        recent = db.get_recent_candles(ticker, timeframe, limit=effective_window + 10)
        result['data_points'] = len(recent)

        if len(recent) < effective_window:
            result['error'] = f"Недостаточно данных: нужно {effective_window}, есть {len(recent)}"
            return result

        if recent and len(recent) >= 2:
            # Если первая свеча новее последней — значит, порядок обратный (DESC)
            if recent[0]['time'] > recent[-1]['time']:
                if show_debug:
                    print(f"🔄 Данные в порядке DESC (новые→старые), разворачиваем в ASC (старые→новые)")
                recent = list(reversed(recent))  # или recent[::-1]

        print(recent)
        print ()
        print()
        print()
        # 2. Готовим данные для стратегии
        #closes = [c['close'] for c in recent]
        closes = get_price_type(recent, price_type='LHCO_Avg')
        print(closes)
        result['price_last'] = closes[-1]

        # 🔥 Отладочный вывод данных
        if show_data:
            print(f"\n📊 Последние 10 свечей ({ticker}/{timeframe}) — порядок: [индекс] время | close")
            print(f"   💡 Ожидаемый порядок: СТАРЫЕ → НОВЫЕ (слева направо)")
            print()

            # Показываем последние 10 с временем
            recent_with_time = recent[-10:]
            for idx, candle in enumerate(recent_with_time, start=len(recent) - 9):
                time_str = candle['time'].strftime("%Y-%m-%d %H:%M") if candle['time'] else "N/A"
                close_val = candle['close']
                print(f"   [{idx:3d}] {time_str} | {close_val:,.4f}")

            # 🔍 Проверка порядка
            if len(recent) >= 2:
                times = [c['time'] for c in recent[-10:] if c['time']]
                if times:
                    if times[0] > times[-1]:
                        print(f"\n⚠️  ВНИМАНИЕ: Время убывает! Данные могут быть в обратном порядке.")
                        print(f"   Первая: {times[0]}, Последняя: {times[-1]}")
                    else:
                        print(f"\n✅ Порядок времени: корректный (растёт слева направо)")
            print()

        # 3. Запускаем стратегию
        if show_debug:
            print(f"🔍 Запуск {strategy_name} (окно={effective_window}, данных={len(closes)})")

        signal = run_strategy(strategy_name, closes)
        result['signal'] = signal
        result['success'] = True

        # 4. Доп. метрики для отладки
        if show_debug and strategy_name == "rsi_oversold":
            # Считаем RSI вручную для проверки
            from strategy import calc_rsi
            rsi_val = calc_rsi(closes)
            result['debug']['rsi_value'] = rsi_val
            print(f"🔍 RSI значение: {rsi_val:.2f}")

        elif show_debug and strategy_name == "sma_cross":
            from strategy import calc_sma
            fast = calc_sma(closes, 9)
            slow = calc_sma(closes, 21)
            result['debug']['sma_fast'] = fast
            result['debug']['sma_slow'] = slow
            print(f"🔍 SMA(9)={fast:.2f}, SMA(21)={slow:.2f}, дифф={fast - slow:.2f}")

        return result

    except Exception as e:
        result['error'] = str(e)
        import traceback
        if show_debug:
            traceback.print_exc()
        return result


# === CLI ИНТЕРФЕЙС ===
def main():
    parser = argparse.ArgumentParser(description="🧪 Атомарный тест стратегий")

    # Обязательные аргументы
    parser.add_argument('-t', '--ticker', required=True, help='Тикер (например, GAZP)')
    parser.add_argument('-tf', '--timeframe', required=True,
                        choices=['1m', '5m', '15m', '1h', '1d'],
                        help='Таймфрейм')
    parser.add_argument('-s', '--strategy', required=True,
                        choices=list(STRATEGY_REGISTRY.keys()),
                        help='Стратегия для теста')

    # Опциональные аргументы
    parser.add_argument('-w', '--window', type=int, default=None,
                        help='Окно стратегии (переопределение дефолта)')
    parser.add_argument('--db-host', type=str, default=None,
                        help='Хост БД (для подключения к реальной)')
    parser.add_argument('--db-name', type=str, default=None,
                        help='Имя БД (для подключения к реальной)')
    parser.add_argument('--config', type=str, default=None,
                        help='Путь к config.yaml (если нужна реальная БД)')

    # Флаги вывода
    parser.add_argument('--show-data', action='store_true',
                        help='Показать последние цены')
    parser.add_argument('--show-debug', action='store_true',
                        help='Показать отладочную информацию (индикаторы)')
    parser.add_argument('--json', action='store_true',
                        help='Вывод в JSON-формате')

    args = parser.parse_args()

    # Заголовок
    print(f"\n🧪 АТОМАРНЫЙ ТЕСТ СТРАТЕГИИ")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Тикер:     {args.ticker}")
    print(f"Таймфрейм: {args.timeframe}")
    print(f"Стратегия: {args.strategy} ({STRATEGY_REGISTRY[args.strategy]})")
    if args.window:
        print(f"Окно:      {args.window} (кастомное)")
    print()

    # Подключение к БД (попытка)
    db = get_real_db(config_path='config.yaml')
    # if args.db_host or args.config:
    #     # 🔥 Здесь можно доработать подключение к реальной БД
    #     # Пока — заглушка
    #     print("⚠️ Подключение к реальной БД пока не реализовано в этом скрипте")
    #     print("💡 Используй MockDB (тестовые данные) или доработай get_real_db()")

    # Запуск теста
    result = run_atomic_test(
        ticker=args.ticker,
        timeframe=args.timeframe,
        strategy_name=args.strategy,
        window=args.window,
        db=db,
        show_data=args.show_data,
        show_debug=args.show_debug
    )

    # Вывод результата
    if args.json:
        import json
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"📈 Результат:")
        print(f"   Статус:   {'✅ ОК' if result['success'] else '❌ ОШИБКА'}")
        if result['error']:
            print(f"   Ошибка:   {result['error']}")
        print(f"   Сигнал:   {result['signal'] or '—'}")
        print(f"   Цена:     {result['price_last'] or '—'}")
        print(f"   Свечей:   {result['data_points']}")

        if result['debug']:
            print(f"   Отладка:  {result['debug']}")

    # Итоговый код выхода
    sys.exit(0 if result['success'] else 1)


if __name__ == "__main__":
    main()