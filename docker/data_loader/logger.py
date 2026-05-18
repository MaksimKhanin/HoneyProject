import os
import logging
from logging.handlers import TimedRotatingFileHandler


def setup_logger(name: str, log_file: str = None, level: str = "INFO", keep_days: int = 3) -> logging.Logger:
    """
    Единый логгер для всего проекта.
    Пишет в файл (с ротацией) и в консоль.

    :param name: Имя логгера
    :param log_file: Путь к файлу логов. Если None - только консоль
    :param level: Уровень логирования
    :param keep_days: Количество дней хранения логов
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Очищаем старые хендлеры (чтобы не дублировать при импорте)
    if logger.hasHandlers():
        logger.handlers.clear()

    # Формат сообщения
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')

    # Файловый хендлер с ротацией (если указан log_file)
    if log_file:
        # Создаем папку для логов
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when='D',
            interval=1,
            backupCount=keep_days,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.suffix = "%Y-%m-%d"
        logger.addHandler(file_handler)

    # Консольный хендлер (всегда добавляем)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger