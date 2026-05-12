#!/bin/bash
# run_tests.sh — удобный запуск интеграционных тестов

set -e  # Выход при ошибке

echo "🔥 Integration Test Runner"
echo "=========================="

# Проверка переменных окружения
if [ -z "$TINKOFF_TOKEN" ]; then
    echo "❌ TINKOFF_TOKEN не установлен"
    exit 1
fi

if [ -z "$DB_PASSWORD" ]; then
    echo "❌ DB_PASSWORD не установлен"
    exit 1
fi

# Параметры по умолчанию
TICKER=${TEST_TICKER:-SBER}
TIMEFRAME=${TEST_TIMEFRAME:-1h}
STRATEGY=${TEST_STRATEGY:-sma_cross}
CLEANUP=${CLEANUP:-false}
REPORT=${REPORT:-true}

echo "📋 Параметры теста:"
echo "   Тикер: $TICKER"
echo "   Таймфрейм: $TIMEFRAME"
echo "   Стратегия: $STRATEGY"
echo "   Очистка после: $CLEANUP"
echo ""

# Запуск теста
CMD="python -m tests.integration_test --ticker $TICKER --timeframe $TIMEFRAME --strategy $STRATEGY"

if [ "$CLEANUP" = "true" ]; then
    CMD="$CMD --cleanup"
fi

if [ "$REPORT" = "false" ]; then
    CMD="$CMD --no-report"
fi

echo "🚀 Запуск: $CMD"
echo ""

$CMD
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "🎉 Тесты пройдены успешно!"
    echo "📄 Отчёт: $(ls -t /var/log/trading/test_reports/*.html | head -1)"
else
    echo "💥 Тесты упали с кодом $EXIT_CODE"
    echo "🔍 Проверьте лог: /var/log/trading/test_integration.log"
fi

exit $EXIT_CODE