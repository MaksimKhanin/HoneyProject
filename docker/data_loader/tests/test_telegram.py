# test_telegram.py
import asyncio
import os
import sys

# 🔥 Добавляем путь к проекту если нужно
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram_notifier import TelegramNotifier


async def main():
    token = '1155052470:AAELrvfzH_h2zMucZ7BTTaKeKS5lI01yrFg'
    chat_id = '-5165853342'

    if token == "YOUR_TOKEN_HERE" or chat_id == "YOUR_CHAT_ID_HERE":
        print("❌ Установи TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в .env!")
        return

    # 🔥 Создаём нотификатор с отключённой проверкой SSL для тестов
    notifier = TelegramNotifier(
        token=token,
        chat_id=chat_id,
        verify_ssl=True  # 🔥 Временно отключаем для обхода SSL-ошибки
    )

    try:
        # Инициализируем сессию
        await notifier.init_session()

        # Тест 1: простое сообщение
        print("📤 Тест 1: простое сообщение...")
        ok = await notifier.send_message(
            "👋 <b>Привет!</b> Это тест от твоего трейдинг-бота.",
            parse_mode="HTML"
        )
        print(f"   Результат: {'✅ ОК' if ok else '❌ FAIL'}")

        await asyncio.sleep(1)  # Не спамим

        # Тест 2: торговый сигнал
        print("📤 Тест 2: торговый сигнал...")
        ok = await notifier.send_signal(
            ticker="GAZP",
            timeframe="1h",
            strategy="rsi_oversold",
            signal="BUY",
            price=152.34,
            candle_time=None,
            extra={"RSI": 28.5, "Объём": "1.2M"}
        )
        print(f"   Результат: {'✅ ОК' if ok else '❌ FAIL'}")

    finally:
        await notifier.close()
        print("✅ Тест завершён")


if __name__ == "__main__":
    asyncio.run(main())