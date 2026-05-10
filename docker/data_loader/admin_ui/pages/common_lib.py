
HEAD_FIX = """
<!-- admin_ui/pages/loader.py, portfolio.py, strategies.py — в <head> -->
<style>

  :root {
    --bg-primary: #1a1a1a;
    --bg-secondary: #252525;
    --bg-tertiary: #2a2a2a;
    --border-color: #444;
    --text-primary: #fff;
    --text-secondary: #aaa;
    --accent: #0d6efd;
  }
  
  body {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
  }
  
  .card, article {
    background: var(--bg-secondary) !important;
    border-color: var(--border-color) !important;
    color: var(--text-primary) !important;
  }
  
  .card header, article header {
    background: var(--bg-tertiary) !important;
    border-bottom-color: var(--border-color) !important;
    color: var(--text-primary) !important;
  }
  
  input, select, button {
    background: #333 !important;
    color: #fff !important;
    border-color: #555 !important;
  }
  
  /* ===== МОБИЛЬНЫЕ СТИЛИ (с сохранением фона) ===== */
  @media (max-width: 768px) {
    body {
      background: var(--bg-primary) !important;  /* ← Явно сохраняем фон */
      padding: 4px !important;
    }
    
    .card, article {
      background: var(--bg-secondary) !important;  /* ← И здесь */
      margin-bottom: 12px !important;
      padding: 12px !important;
    }

  /* ===== MOBILE-FIRST BASE ===== */
  :root {
    --spacing-sm: 8px;
    --spacing-md: 12px;
    --spacing-lg: 16px;
    --input-min-height: 44px; /* Apple HIG для тач-интерфейсов */
    --font-size-base: 16px;   /* Чтобы не зумило на iOS */
  }

  /* Базовые улучшения для мобильных */
  @media (max-width: 768px) {
    body {
      padding: 4px !important;
      font-size: var(--font-size-base) !important;
    }

    /* Карточки: одна колонка, больше отступов */
    .card, article {
      margin-bottom: 12px !important;
      padding: 12px !important;
    }

    /* Заголовки карточек: перенос текста */
    .card header, article header {
      flex-wrap: wrap !important;
      gap: 8px !important;
    }

    /* Таблицы: горизонтальный скролл */
    .table-responsive {
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
      margin: 0 -12px; /* Компенсация отступов карточки */
      padding: 0 12px;
    }
    .table-responsive table {
      min-width: 600px; /* Мин. ширина для читаемости */
      font-size: 0.9em;
    }

    /* Инпуты: больше, с нумерической клавиатурой */
    input[type="number"], input[type="text"], select {
      min-height: var(--input-min-height) !important;
      font-size: 16px !important;
      padding: 10px 12px !important;
    }
    input[type="number"] {
      inputmode: numeric;
      -moz-appearance: textfield;
    }
    input[type="number"]::-webkit-outer-spin-button,
    input[type="number"]::-webkit-inner-spin-button {
      -webkit-appearance: none;
      margin: 0;
    }

    /* Кнопки: тач-френдли */
    button, .contrast, .secondary {
      min-height: var(--input-min-height) !important;
      padding: 12px 16px !important;
      font-size: 16px !important;
    }

    /* Навигация: горизонтальный скролл или гамбургер */
    nav[role="navigation"] {
      overflow-x: auto !important;
      white-space: nowrap !important;
      -webkit-overflow-scrolling: touch;
      padding-bottom: 4px;
    }
    nav[role="navigation"] a {
      display: inline-block !important;
      margin-right: 8px !important;
      padding: 8px 12px !important;
    }

    /* Grid-сетки: перестраиваем в колонку */
    .grid-5, [style*="grid-template-columns:repeat(5"] {
      grid-template-columns: 1fr !important;
      gap: 12px !important;
    }
    .grid-2, [style*="grid-template-columns:1fr 1fr"] {
      grid-template-columns: 1fr !important;
    }

    /* Метрики: вертикальный список */
    .metrics-container {
      display: flex !important;
      flex-direction: column !important;
      gap: 16px !important;
    }
    .metrics-card {
      width: 100% !important;
    }
    .metrics-grid {
      grid-template-columns: 1fr 1fr !important; /* 2 колонки на мобильном */
      gap: 12px !important;
    }
  }

  /* ===== DESKTOP ENHANCEMENTS ===== */
  @media (min-width: 769px) {
    .metrics-grid {
      grid-template-columns: repeat(4, 1fr) !important;
    }
  }
  
    /* Навигация: адаптивная */
  .navbar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 4px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    white-space: nowrap;
  }
  .navbar a {
    display: inline-flex;
    align-items: center;
    padding: 10px 14px;
    border-radius: 6px;
    font-size: 0.95em;
    min-height: 44px;
    text-decoration: none;
  }
  .navbar a.active {
    background: #0d6efd !important;
    color: #fff !important;
  }
  
  @media (max-width: 480px) {
    .navbar {
      gap: 4px;
      padding: 4px 2px;
    }
    .navbar a {
      padding: 8px 10px;
      font-size: 0.9em;
    }
  }
  
  
</style>
"""