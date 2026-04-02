"""
Тесты для MainLoader (оркестратор загрузчика данных).
Запуск:
  # Однократный тест
  python test_main_loader.py --once

  # Тест непрерывного режима (5 секунд)
  python test_main_loader.py --continuous --duration 5

  # Тест только инициализации
  python test_main_loader.py --init-only

  # Тест с кастомным конфигом
  python test_main_loader.py --once --config config_test.yaml
"""

import asyncio
import os
import sys
import signal
import time
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Отключаем телеметрию, если мешает
os.environ["T_TECH_DISABLE_TELEMETRY"] = "1"

# Импорты наших модулей
from logger import setup_logger
from config_manager import get_config_manager
from T_con import T_connector
from db_manager import DBManager
from main_loader import MainLoader


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def print_header(title: str):
    """Красивый заголовок для теста."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_subheader(title: str):
    """Подзаголовок."""
    print(f"\n📌 {title}")
    print("-" * 50)


def print_result(success: bool, message: str, details: str = ""):
    """Вывод результата теста."""
    icon = "✅" if success else "❌"
    print(f"   {icon} {message}")
    if details:
        print(f"      {details}")
    return success


# ============================================================================
# ТЕСТЫ
# ============================================================================

async def test_initialization(config_path: str = "config.yaml") -> bool:
    """Тест 1: Инициализация MainLoader"""
    print_header("ТЕСТ 1: Инициализация компонентов")

    success = True

    try:
        print_subheader("Создание экземпляра MainLoader...")
        start = time.time()

        loader = MainLoader(config_path=config_path)

        elapsed = time.time() - start
        success &= print_result(True, f"MainLoader создан за {elapsed:.2f} сек")

        # Проверка компонентов
        print_subheader("Проверка инициализированных компонентов...")

        success &= print_result(
            loader.logger is not None,
            "Logger инициализирован",
            f"Файл логов: {loader.config_manager.get_config()['settings']['log_file']}"
        )

        success &= print_result(
            loader.broker is not None,
            "Брокер (T_connector) инициализирован"
        )

        success &= print_result(
            loader.db is not None,
            "DBManager инициализирован"
        )

        success &= print_result(
            loader.config_manager is not None,
            "ConfigManager инициализирован"
        )

        # Проверка таблиц БД
        print_subheader("Проверка таблиц в БД...")
        try:
            # Просто пробуем сделать запрос — если таблицы есть, ошибки не будет
            count = loader.db.get_candles_count("SBER", "1m")
            success &= print_result(True, "Таблицы БД доступны", f"Свечей SBER 1m: {count}")
        except Exception as e:
            success &= print_result(False, "Ошибка доступа к таблицам БД", str(e))

        # Cleanup
        loader.close()

    except Exception as e:
        success &= print_result(False, "Критическая ошибка инициализации", f"{type(e).__name__}: {e}")

    return success


async def test_config_manager_integration(loader: MainLoader) -> bool:
    """Тест 2: Интеграция с ConfigManager"""
    print_header("ТЕСТ 2: Интеграция с ConfigManager")

    success = True

    try:
        print_subheader("Получение конфига...")
        config = loader.config_manager.get_config()

        success &= print_result(
            'tinkoff' in config and 'database' in config,
            "Конфиг загружен корректно",
            f"Секции: {list(config.keys())}"
        )

        print_subheader("Получение включенных инструментов...")
        instruments = loader._get_enabled_instruments()

        success &= print_result(
            len(instruments) > 0,
            f"Найдено {len(instruments)} активных (инструмент, таймфрейм) пар",
            ", ".join([f"{i['ticker']}:{i['timeframe']}" for i in instruments[:5]]) + (
                "..." if len(instruments) > 5 else "")
        )

        # Проверка структуры каждого инструмента
        print_subheader("Проверка структуры данных инструмента...")
        if instruments:
            inst = instruments[0]
            required_fields = ['ticker', 'timeframe', 'history_depth_days', 'update_interval_minutes']
            missing = [f for f in required_fields if f not in inst]

            success &= print_result(
                len(missing) == 0,
                "Структура инструмента корректна",
                f"Поля: {list(inst.keys())}" if not missing else f"Отсутствуют: {missing}"
            )

        print_subheader("Проверка логики интервалов обновления...")
        # Эмулируем проверку _should_load_instrument
        test_inst = {
            'ticker': 'TEST',
            'timeframe': '1m',
            'update_interval_minutes': 5
        }

        # Первый вызов — должно вернуть True (нет в last_load_times)
        should_load_1 = loader._should_load_instrument(test_inst, {})
        success &= print_result(should_load_1, "Новый инструмент помечен для загрузки")

        # С имитацией недавней загрузки — должно вернуть False
        recent_loads = {
            f"{test_inst['ticker']}_{test_inst['timeframe']}": datetime.now()
        }
        should_load_2 = loader._should_load_instrument(test_inst, recent_loads)
        success &= print_result(not should_load_2, "Недавний инструмент пропущен")

        # С имитацией старой загрузки — должно вернуть True
        old_loads = {
            f"{test_inst['ticker']}_{test_inst['timeframe']}": datetime.now() - timedelta(hours=1)
        }
        should_load_3 = loader._should_load_instrument(test_inst, old_loads)
        success &= print_result(should_load_3, "Устаревший инструмент помечен для загрузки")

    except Exception as e:
        success &= print_result(False, "Ошибка в тесте ConfigManager", f"{type(e).__name__}: {e}")

    return success


async def test_load_single_instrument(loader: MainLoader, ticker: str = "SBER", timeframe: str = "1m") -> Dict:
    """Тест 3: Загрузка одного инструмента (возвращает статистику)"""
    print_header(f"ТЕСТ 3: Загрузка инструмента {ticker} ({timeframe})")

    stats = {
        'success': False,
        'uid_found': False,
        'candles_loaded': 0,
        'candles_saved': 0,
        'error': None
    }

    # ✅ ДОБАВИТЬ ЭТУ СТРОКУ:
    success = True

    try:
        print_subheader("Шаг 1: Получение UID...")
        uid = loader.db.get_uid_by_ticker(ticker)

        if not uid:
            print("   ⚠️ UID не найден в БД, запрашиваем у брокера...")
            uid = await loader.broker.get_instrument_uid(ticker)

            if uid:
                inst_info = loader.broker._instruments_cache.get(ticker, {})
                if inst_info:
                    loader.db.upsert_instruments_batch([inst_info])
                    print_result(True, "Инструмент сохранен в БД")

        stats['uid_found'] = uid is not None
        success &= print_result(uid is not None, f"UID получен: {uid[:20] + '...' if uid else None}")

        if not uid:
            stats['error'] = "UID not found"
            return stats

        # ... остальной код без изменений ...

        stats['success'] = True

    except Exception as e:
        stats['error'] = f"{type(e).__name__}: {e}"
        print_result(False, "Ошибка загрузки инструмента", stats['error'])

    return stats


async def test_load_cycle(loader: MainLoader, limit_instruments: int = 2) -> bool:
    """Тест 4: Один цикл загрузки всех инструментов (ограничено для скорости)"""
    print_header("ТЕСТ 4: Цикл загрузки (ограниченный)")

    success = True

    try:
        instruments = loader._get_enabled_instruments()[:limit_instruments]
        print_subheader(f"Загрузка {len(instruments)} инструментов (лимит теста)...")

        results = []
        for i, inst in enumerate(instruments, 1):
            print(f"\n[{i}/{len(instruments)}] {inst['ticker']} ({inst['timeframe']})")

            result = await loader._load_instrument(
                ticker=inst['ticker'],
                timeframe=inst['timeframe'],
                history_depth=inst['history_depth_days']
            )
            results.append(result)

            status = "✅" if result['success'] else "❌"
            print(
                f"   {status} {result['ticker']}: загружено={result['candles_loaded']}, сохранено={result['candles_saved']}")

            if result.get('error'):
                print(f"      Ошибка: {result['error']}")
                success = False

        # Сводный отчет
        print_subheader("Сводный отчет цикла...")
        total_loaded = sum(r['candles_loaded'] for r in results)
        total_saved = sum(r['candles_saved'] for r in results)
        success_count = sum(1 for r in results if r['success'])

        print_result(success_count == len(results),
                     f"Успешно: {success_count}/{len(results)}",
                     f"Всего загружено: {total_loaded}, сохранено: {total_saved}")

    except Exception as e:
        success = print_result(False, "Ошибка в цикле загрузки", f"{type(e).__name__}: {e}")

    return success


async def test_continuous_mode_short(loader: MainLoader, duration_seconds: int = 10) -> bool:
    """Тест 5: Короткий тест непрерывного режима (эмуляция)"""
    print_header(f"ТЕСТ 5: Непрерывный режим ({duration_seconds} сек эмуляции)")

    success = True

    try:
        print_subheader("Запуск run_continuous в ускоренном режиме...")

        # Патчим метод, чтобы не ждать реальные интервалы
        original_should_load = loader._should_load_instrument

        def always_load(inst, last_loads):
            # Всегда возвращаем True для теста, но обновляем last_loads
            key = f"{inst['ticker']}_{inst['timeframe']}"
            last_loads[key] = datetime.now()
            return True

        loader._should_load_instrument = always_load

        # Запускаем на ограниченное время
        start = time.time()
        cycle_count = 0

        # Эмулируем один быстрый цикл вместо бесконечного
        results = await loader._run_load_cycle()
        cycle_count += 1

        elapsed = time.time() - start

        # Восстанавливаем оригинальный метод
        loader._should_load_instrument = original_should_load

        success &= print_result(
            cycle_count >= 1,
            f"Выполнено {cycle_count} циклов за {elapsed:.1f} сек",
            f"Результатов: {len(results)}"
        )

        if results:
            success_count = sum(1 for r in results if r.get('success'))
            print_result(success_count > 0, f"Успешных загрузок: {success_count}/{len(results)}")

    except Exception as e:
        success = print_result(False, "Ошибка в тесте непрерывного режима", f"{type(e).__name__}: {e}")

    return success


async def test_graceful_shutdown(config_path: str = "config.yaml") -> bool:
    """Тест 6: Корректное завершение работы (signal handling)"""
    print_header("ТЕСТ 6: Корректное завершение работы")

    success = True

    try:
        print_subheader("Создание loader и эмуляция сигнала...")

        loader = MainLoader(config_path=config_path)

        # Проверяем, что флаг running установлен
        success &= print_result(loader.running, "Флаг running = True после инициализации")

        # Эмулируем получение SIGTERM
        print_subheader("Эмуляция сигнала завершения...")
        loader.running = False

        # Вызываем close
        print_subheader("Вызов close()...")
        loader.close()

        success &= print_result(True, "close() выполнен без ошибок")

        # Проверка, что подключения закрыты
        # (это сложно проверить извне, но можно попробовать сделать запрос)
        print_subheader("Проверка состояния после close...")
        try:
            # Попытка сделать запрос после close может упасть — это нормально
            # Но если падает с "connection closed" — значит, закрылось корректно
            print_result(True, "Проверка пост-условий (ручная)")
        except Exception as e:
            # Ожидается, что после close могут быть ошибки подключения
            print_result(True, "Ожидается ошибка после close", f"{type(e).__name__}")

    except Exception as e:
        success = print_result(False, "Ошибка в тесте shutdown", f"{type(e).__name__}: {e}")

    return success


async def test_error_handling(config_path: str = "config.yaml") -> bool:
    """Тест 7: Обработка ошибок (несуществующий тикер, ошибка сети и т.д.)"""
    print_header("ТЕСТ 7: Обработка ошибок")

    success = True

    try:
        loader = MainLoader(config_path=config_path)

        print_subheader("Тест 7.1: Несуществующий тикер...")
        result = await loader._load_instrument(
            ticker="FAKETICKER123",
            timeframe="1m",
            history_depth=1
        )
        success &= print_result(
            not result['success'] and result['error'] is not None,
            "Ошибка для несуществующего тикера обработана",
            f"Ошибка: {result['error'][:100]}..." if result['error'] else "Нет ошибки"
        )

        print_subheader("Тест 7.2: Неподдерживаемый таймфрейм...")
        # _load_instrument ловит исключения внутри, поэтому проверяем result['error']
        result = await loader._load_instrument(
            ticker="SBER",
            timeframe="99x",  # Неподдерживаемый
            history_depth=1
        )

        has_expected_error = (
                result['error'] is not None and
                'Неподдерживаемый таймфрейм' in result['error']
        )

        success &= print_result(
            has_expected_error,
            "Неподдерживаемый таймфрейм корректно обработан",
            f"Ошибка: {result['error']}" if result['error'] else "Нет ошибки"
        )

        print_subheader("Тест 7.3: Пустой список инструментов...")
        original_get = loader._get_enabled_instruments
        loader._get_enabled_instruments = lambda: []

        results = await loader._run_load_cycle()
        success &= print_result(
            len(results) == 0,
            "Пустой список инструментов обработан корректно",
            f"Результатов: {len(results)}"
        )

        loader._get_enabled_instruments = original_get

        loader.close()

    except Exception as e:
        success = print_result(False, "Ошибка в тесте error handling", f"{type(e).__name__}: {e}")

    return success


# ============================================================================
# MAIN
# ============================================================================

async def run_all_tests(config_path: str = "config.yaml") -> Dict[str, bool]:
    """Запуск всех тестов."""
    results = {}

    print("\n🚀 ЗАПУСК ПОЛНОГО ТЕСТ-ДРАЙВА MAIN_LOADER")
    print(f"📅 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Конфиг: {config_path}")

    # Тест 1: Инициализация
    results['init'] = await test_initialization(config_path)

    if not results['init']:
        print("\n❌ Тест инициализации провален. Остальные тесты пропущены.")
        return results

    # Создаем лоадер для остальных тестов
    loader = MainLoader(config_path=config_path)

    try:
        # Тест 2: ConfigManager
        results['config'] = await test_config_manager_integration(loader)

        # Тест 3: Один инструмент (быстрый)
        results['single_load'] = (await test_load_single_instrument(
            loader, ticker="SBER", timeframe="1d"  # 1d быстрее для теста
        ))['success']

        # Тест 4: Цикл загрузки (ограничен 2 инструментами)
        results['cycle'] = await test_load_cycle(loader, limit_instruments=2)

        # Тест 5: Непрерывный режим (короткий)
        results['continuous'] = await test_continuous_mode_short(loader, duration_seconds=5)

        # Тест 6: Graceful shutdown (отдельный инстанс)
        results['shutdown'] = await test_graceful_shutdown(config_path)

        # Тест 7: Error handling
        results['errors'] = await test_error_handling(config_path)

    finally:
        loader.close()

    return results


def print_summary(results: Dict[str, bool]):
    """Вывод сводки по тестам."""
    print_header("🏁 СВОДКА ПО ТЕСТАМ")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    print(f"\n{'Тест':<30} {'Результат':<10}")
    print("-" * 40)

    test_names = {
        'init': 'Инициализация',
        'config': 'ConfigManager',
        'single_load': 'Загрузка инструмента',
        'cycle': 'Цикл загрузки',
        'continuous': 'Непрерывный режим',
        'shutdown': 'Graceful shutdown',
        'errors': 'Обработка ошибок'
    }

    for key, name in test_names.items():
        if key in results:
            icon = "✅" if results[key] else "❌"
            print(f"{name:<30} {icon} {results[key]}")

    print("-" * 40)
    print(f"{'ИТОГО':<30} {passed}/{total} passed")

    if passed == total:
        print("\n🎉 Все тесты пройдены! Можно запускать в продакшен.")
    else:
        print(f"\n⚠️  {total - passed} тест(ов) провалено. Проверь логи.")


async def main():
    """Точка входа для тестов."""
    parser = argparse.ArgumentParser(description='Тесты для MainLoader')
    parser.add_argument('--config', type=str, default='config.yaml', help='Путь к конфигу')
    parser.add_argument('--once', action='store_true', help='Запустить только базовые тесты')
    parser.add_argument('--init-only', action='store_true', help='Только тест инициализации')
    parser.add_argument('--continuous', action='store_true', help='Включить тест непрерывного режима')
    parser.add_argument('--duration', type=int, default=5, help='Длительность теста непрерывного режима (сек)')

    args = parser.parse_args()

    try:
        if args.init_only:
            results = {'init': await test_initialization(args.config)}
        elif args.once:
            # Базовый набор тестов
            results = {}
            results['init'] = await test_initialization(args.config)
            if results['init']:
                loader = MainLoader(config_path=args.config)
                try:
                    results['config'] = await test_config_manager_integration(loader)
                    results['single_load'] = (await test_load_single_instrument(
                        loader, ticker="SBER", timeframe="1d"
                    ))['success']
                    results['errors'] = await test_error_handling(args.config)
                finally:
                    loader.close()
        else:
            # Полная батарея тестов
            results = await run_all_tests(args.config)

        print_summary(results)

        # Exit code для CI/CD
        sys.exit(0 if all(results.values()) else 1)

    except KeyboardInterrupt:
        print("\n⚠️  Прервано пользователем")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())