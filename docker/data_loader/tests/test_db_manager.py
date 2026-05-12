import asyncio
from T_con import T_connector
from db_manager import DBManager


async def main():
    print("\n🚀 ТЕСТ ОПТИМИЗИРОВАННОЙ БД\n")

    broker = T_connector()
    db = DBManager()

    try:
        # 1. Создание таблиц
        print("=== 1. Создание таблиц ===")
        db.create_tables()
        print("✅ Таблицы созданы\n")

        # 2. Сохранение инструментов
        print("=== 2. Сохранение инструментов ===")
        await broker.refresh_instruments_cache()

        instruments_to_save = [broker._instruments_cache[t] for t in ["SBER", "GAZP"] if t in broker._instruments_cache]
        saved = db.upsert_instruments_batch(instruments_to_save)
        print(f"✅ Сохранено инструментов: {saved}\n")

        # 3. Загрузка и сохранение свечей
        print("=== 3. Загрузка и сохранение свечей ===")

        # Получаем UID из БД (а не от брокера)
        uid = db.get_uid_by_ticker("SBER")
        if not uid:
            uid = await broker.get_instrument_uid("SBER")

        last_date = db.get_last_candle_date("SBER", "1m")
        print(f"Последняя свеча в БД: {last_date}")

        candles = await broker.load_historical_data(
            ticker="SBER",
            uid=uid,
            timeframe="1m",
            last_known_date=last_date
        )

        if candles:
            # ТЕПЕРЬ ПРОЩЕ: нет instrument_uid
            saved_candles = db.save_candles(
                candles_list=candles,
                ticker="SBER",
                timeframe="1m"
            )
            print(f"✅ Сохранено/обновлено свечей: {saved_candles}")

        # 4. Статистика
        print("\n=== 4. Статистика ===")
        count = db.get_candles_count("SBER", "1m")
        print(f"Всего свечей SBER 1m: {count}")

        date_range = db.get_date_range("SBER", "1m")
        if date_range[0]:
            print(f"Диапазон: {date_range[0]} → {date_range[1]}")

        # 5. Последние свечи
        print("\n=== 5. Последние 5 свечей ===")
        recent = db.get_recent_candles("SBER", "1m", limit=5)
        for c in recent:
            print(f"   {c['time']} | O:{c['open']} C:{c['close']}")

        print("\n🏁 ТЕСТ ЗАВЕРШЕН")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())