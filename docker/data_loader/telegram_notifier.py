# telegram_notifier.py
"""
Минималистичный асинхронный нотификатор для Telegram.
Без внешних зависимостей сверх aiohttp.
"""

import aiohttp
from typing import Optional, Dict, Any
from datetime import datetime
from logger import setup_logger


class TelegramNotifier:
    """Асинхронный отправитель сообщений в Telegram."""

    BASE_URL = "https://api.telegram.org/bot"

    def __init__(self, token: str, chat_id: str, timeout: int = 10, verify_ssl: bool = True):
        if not token or not chat_id:
            raise ValueError("Telegram token и chat_id обязательны!")

        self.token = token.strip()
        self.chat_id = str(chat_id).strip()
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._session: Optional[aiohttp.ClientSession] = None

        # Логгер
        self.logger = setup_logger(name="TelegramNotifier",
                                   log_file="logs/Telegram.log",
                                   level="INFO")

        self.logger.info(f"🤖 TelegramNotifier инициализирован (chat_id: {self._mask_chat_id()})")

    def _mask_chat_id(self) -> str:
        """Маскирует chat_id для логов."""
        cid = self.chat_id
        if len(cid) > 6:
            return cid[:3] + "..." + cid[-3:]
        return "***"

    async def init_session(self):
        """Явная инициализация сессии (вызывать внутри async-контекста)."""
        if self._session is None or self._session.closed:
            try:
                # Создаём connector с настройками SSL
                if self.verify_ssl:
                    connector = aiohttp.TCPConnector()
                else:
                    # 🔥 Отключаем проверку SSL (ТОЛЬКО ДЛЯ ТЕСТОВ!)
                    connector = aiohttp.TCPConnector(ssl=False)
                    self.logger.warning("⚠️ SSL-проверка отключена! Не используй в продакшене.")

                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    connector=connector
                )
                self.logger.debug("✅ aiohttp session создан")
            except Exception as e:
                self.logger.error(f"❌ Ошибка создания сессии: {e}", exc_info=True)
                raise

    async def send_message(self, text: str, parse_mode: str = "HTML",
                           disable_notification: bool = False) -> bool:
        """
        Отправляет сообщение в чат.
        """
        # Обрезаем если слишком длинное
        if len(text) > 4096:
            text = text[:4093] + "..."
            self.logger.warning("✂️ Сообщение обрезано до 4096 символов")

        # 🔥 Гарантируем, что сессия создана
        if self._session is None or self._session.closed:
            await self.init_session()

        url = f"{self.BASE_URL}{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
            "disable_notification": disable_notification
        }

        try:
            async with self._session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self.logger.debug(f"✅ Сообщение отправлено: {text[:50]}...")
                        return True
                    else:
                        self.logger.error(f"❌ Telegram API error: {data.get('description')}")
                        return False
                else:
                    error_text = await resp.text()
                    self.logger.error(f"❌ HTTP {resp.status}: {error_text}")
                    return False
        except aiohttp.ClientError as e:
            self.logger.error(f"❌ Network error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Unexpected error: {e}", exc_info=True)
            return False

    async def send_signal(self,
                          ticker: str,
                          timeframe: str,
                          strategy: str,
                          signal: str,
                          price: float,
                          candle_time: Optional[datetime],
                          extra: Optional[Dict[str, Any]] = None) -> bool:
        """Форматирует и отправляет торговый сигнал."""
        signal_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(signal, "⚪")

        time_str = candle_time.strftime("%Y-%m-%d %H:%M") if candle_time else "N/A"

        msg = (
            f"{signal_emoji} <b>{signal}</b> сигнал по <b>{ticker}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 Таймфрейм: <code>{timeframe}</code>\n"
            f"🧠 Стратегия: <code>{strategy}</code>\n"
            f"💰 Цена: <b>{price:,.2f}</b>\n"
            f"🕐 Свеча: <code>{time_str}</code>"
        )

        if extra:
            extra_lines = [f"{k}: <code>{v}</code>" for k, v in extra.items() if v is not None]
            if extra_lines:
                msg += "\n" + "\n".join(extra_lines)

        self.logger.info(f"📤 Отправка сигнала: {ticker}/{timeframe} {signal} @ {price}")
        return await self.send_message(msg)

    async def send_error(self, error_text: str, context: str = "") -> bool:
        """Отправляет сообщение об ошибке."""
        msg = (
            f"🔴 <b>Ошибка в трейдинг-системе</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<code>{context}</code>\n\n"
            f"❗ <b>{error_text}</b>"
        )
        return await self.send_message(msg)

    async def close(self):
        """Закрывает сессию."""
        if self._session and not self._session.closed:
            await self._session.close()
            self.logger.info("🔌 TelegramNotifier: сессия закрыта")

    async def __aenter__(self):
        await self.init_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False