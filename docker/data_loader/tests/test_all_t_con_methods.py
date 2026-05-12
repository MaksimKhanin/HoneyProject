"""
Тесты для T_connector с новой архитектурой (ConfigManager + кэширование).
Запуск: python test_all_t_con_methods.py
"""

import asyncio
import os
from datetime import datetime, timedelta
from T_con import T_connector

# Отключаем телеметрию, если мешает
os.environ["T_TECH_DISABLE_TELEMETRY"] = "1"


async def test_get_instrument_uid(broker: T_connector):
    """Тест 1: Получение UID по тикеру с кэшированием"""
    print("\n" + "=" * 60)
    print("ТЕСТ 1: get_instrument_uid() — с кэшированием")
    print("=" * 60)

    tickers = ["SBER", "GAZP", "VTBR", "NONEXISTENT123"]

    for ticker in tickers:
        print(f"\n🔍 Поиск: {ticker}")
        uid = await broker.get_instrument_uid(ticker)
        if uid:
            print(f"   ✅ {ticker} -> UID: {uid}")
        else:
            print(f"   ❌ {ticker} -> не найден")

    # Проверка кэша: второй запрос должен быть мгновенным
    # (кэширование теперь всегда включено по умолчанию)
    print(f"\n⚡ Проверка кэша для SBER (должно быть мгновенно)...")
    start = datetime.now()
    uid_cached = await broker.get_instrument_uid("SBER")  # Без use_cache параметра
    elapsed = (datetime.now() - start).total_seconds()

    status = "✅ кэш" if elapsed < 0.1 else "⏳ запрос"
    print(f"   Время выполнения: {elapsed:.4f} сек ({status})")

    if elapsed >= 0.1:
        print("   ⚠️ Кэш мог не сработать — проверь логи")


async def test_get_instruments_from_config(broker: T_connector):
    """Тест 2: Получение инструментов из конфига (синхронный метод)"""
    print("\n" + "=" * 60)
    print("ТЕСТ 2: get_instruments_from_config()")
    print("=" * 60)

    # Сначала убеждаемся, что кэш загружен (вызываем для любого тикера)
    print("🔄 Предварительная загрузка кэша...")
    await broker.get_instrument_uid("SBER")

    # Получаем инструменты из конфига (синхронный вызов!)
    print("📋 Получение списка из конфига...")
    instruments = broker.get_instruments_from_config()  # ✅ Не async!

    if not instruments:
        print("   ⚠️ Нет инструментов в конфиге или кэш пуст")
        return

    print(f"\n📊 Найдено инструментов: {len(instruments)}\n")
    print(f"{'Тикер':<10} {'UID':<40} {'Тип':<10} {'Валюта':<6}")
    print("-" * 70)

    for inst in instruments:
        print(f"{inst['ticker']:<10} {inst['uid']:<40} {inst['type']:<10} {inst['currency']:<6}")


async def test_fetch_candles_chunk(broker: T_connector):
    """Тест 3: Загрузка одного куска свечей (низкоуровневый метод)"""
    print("\n" + "=" * 60)
    print("ТЕСТ 3: fetch_candles_chunk()")
    print("=" * 60)

    from t_tech.invest import CandleInterval

    # Получаем UID (используем кэш)
    print("🔍 Получение UID для SBER...")
    uid = await broker.get_instrument_uid("SBER")

    if not uid:
        print("   ❌ Не удалось получить UID для SBER, пропускаем тест")
        return

    # Запрашиваем 1 час минутных свечей (вчера с 10:00 до 11:00)
    from_date = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) - timedelta(days=1)
    to_date = from_date + timedelta(hours=1)

    print(f"\n🕐 Запрос: {from_date} → {to_date}")
    print(f"📈 Интервал: 1 минута")

    try:
        candles = await broker.fetch_candles_chunk(
            uid=uid,
            interval=CandleInterval.CANDLE_INTERVAL_1_MIN,
            from_date=from_date,
            to_date=to_date
        )

        print(f"\n✅ Получено свечей: {len(candles)}")

        if candles:
            print(f"\n📊 Первая свеча:")
            print(f"   Time:  {candles[0]['time']}")
            print(f"   Open:  {candles[0]['open']}")
            print(f"   High:  {candles[0]['high']}")
            print(f"   Low:   {candles[0]['low']}")
            print(f"   Close: {candles[0]['close']}")
            print(f"   Volume: {candles[0]['volume']}")

            print(f"\n📊 Последняя свеча:")
            print(f"   Time:  {candles[-1]['time']}")
            print(f"   Close: {candles[-1]['close']}")
        else:
            print("   ⚠️ Рынок закрыт или нет данных за этот период")

    except Exception as e:
        print(f"   ❌ Ошибка: {e}")


async def test_load_historical_data(broker: T_connector):
    """Тест 4: Полная загрузка истории с инкрементальной логикой"""
    print("\n" + "=" * 60)
    print("ТЕСТ 4: load_historical_data()")
    print("=" * 60)

    uid = await broker.get_instrument_uid("SBER")
    if not uid:
        print("   ❌ Не удалось получить UID, пропускаем")
        return

    # Сценарий А: Полная загрузка за 3 дня (для теста быстро)
    print(f"\n🔄 Сценарий А: Полная загрузка за 3 дня (1m свечи)")
    start = datetime.now()

    candles_full = await broker.load_historical_data(
        ticker="SBER",
        uid=uid,
        timeframe="1m",
        last_known_date=None  # Нет данных — грузим всё
    )

    elapsed = (datetime.now() - start).total_seconds()
    print(f"   ⏱️  Время: {elapsed:.1f} сек")
    print(f"   📊 Всего свечей: {len(candles_full)}")

    if candles_full:
        print(f"   📅 Диапазон: {candles_full[0]['time']} → {candles_full[-1]['time']}")

    # Сценарий Б: Инкрементальная загрузка (от последней свечи)
    if candles_full:
        last_date = candles_full[-1]['time']
        print(f"\n🔄 Сценарий Б: Инкрементальное обновление от {last_date}")
        start = datetime.now()

        candles_incremental = await broker.load_historical_data(
            ticker="SBER",
            uid=uid,
            timeframe="1m",
            last_known_date=last_date  # Есть точка отсчета
        )

        elapsed = (datetime.now() - start).total_seconds()
        print(f"   ⏱️  Время: {elapsed:.1f} сек")
        print(f"   📊 Новые свечи: {len(candles_incremental)}")

    # Сценарий В: Другой таймфрейм (5 минут)
    print(f"\n🔄 Сценарий В: Загрузка 5m свечей за 7 дней")
    start = datetime.now()

    candles_5m = await broker.load_historical_data(
        ticker="SBER",
        uid=uid,
        timeframe="5m",
        last_known_date=datetime.now() - timedelta(days=7)
    )

    elapsed = (datetime.now() - start).total_seconds()
    print(f"   ⏱️  Время: {elapsed:.1f} сек")
    print(f"   📊 Всего 5m свечей: {len(candles_5m)}")


async def test_refresh_instruments_cache(broker: T_connector):
    """Тест 5: Принудительное обновление кэша"""
    print("\n" + "=" * 60)
    print("ТЕСТ 5: refresh_instruments_cache()")
    print("=" * 60)

    print(f"\n🔄 Принудительное обновление кэша...")
    start = datetime.now()

    cache = await broker.refresh_instruments_cache()

    elapsed = (datetime.now() - start).total_seconds()
    print(f"   ⏱️  Время: {elapsed:.1f} сек")
    print(f"   📦 Инструментов в кэше: {len(cache)}")

    # Показать несколько примеров из кэша
    print(f"\n📋 Примеры из кэша:")
    sample_tickers = ["SBER", "GAZP", "USDRUB"]
    for ticker in sample_tickers:
        if ticker in cache:
            inst = cache[ticker]
            print(f"   {ticker:<10} | {inst['name']:<30} | {inst['type']:<10}")
        else:
            print(f"   {ticker:<10} | не найден в кэше")


async def test_edge_cases(broker: T_connector):
    """Тест 6: Граничные случаи и ошибки"""
    print("\n" + "=" * 60)
    print("ТЕСТ 6: Обработка ошибок и граничные случаи")
    print("=" * 60)

    # Несуществующий тикер
    print(f"\n❓ Поиск несуществующего тикера 'FAKETICKER123'...")
    uid = await broker.get_instrument_uid("FAKETICKER123")
    status = "✅ корректно" if uid is None else "⚠️ странно"
    print(f"   Результат: {uid} ({status})")

    # Неподдерживаемый таймфрейм
    print(f"\n❓ Загрузка с неподдерживаемым таймфреймом '99m'...")
    try:
        await broker.load_historical_data(
            ticker="SBER",
            uid="dummy_uid",
            timeframe="99m"
        )
        print("   ⚠️ Ошибка не выброшена (возможно, обработка внутри)")
    except ValueError as e:
        print(f"   ✅ Ошибка корректно обработана: {e}")
    except Exception as e:
        print(f"   ⚠️ Другая ошибка: {type(e).__name__}: {e}")

    # Пустой UID
    print(f"\n❓ Загрузка с пустым UID...")
    try:
        candles = await broker.load_historical_data(
            ticker="SBER",
            uid="",
            timeframe="1m"
        )
        print(f"   Результат: {len(candles)} свечей")
    except Exception as e:
        print(f"   ✅ Ошибка корректно обработана: {type(e).__name__}")


async def main():
    """Главная точка входа — запускает все тесты"""
    print("\n🚀 ЗАПУСК ПОЛНОГО ТЕСТ-ДРАЙВА T_CONNECTOR")
    print(f"📅 Время старта: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Конфиг: config.yaml")

    # Инициализация брокера
    try:
        broker = T_connector(config_path="../../../config.yaml")
        print("✅ Брокер инициализирован успешно")
    except Exception as e:
        print(f"❌ Ошибка инициализации брокера: {e}")
        return

    # Запуск тестов по порядку
    await test_get_instrument_uid(broker)
    await test_get_instruments_from_config(broker)  # ✅ Обновленное имя
    await test_fetch_candles_chunk(broker)
    await test_load_historical_data(broker)
    await test_refresh_instruments_cache(broker)
    await test_edge_cases(broker)

    # Финальный отчет
    print("\n" + "=" * 60)
    print("🏁 ТЕСТ-ДРАЙВ ЗАВЕРШЕН")
    print("=" * 60)
    print(f"📅 Время окончания: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Логи сохранены в: {broker.config['settings']['log_file']}")


if __name__ == "__main__":
    asyncio.run(main())