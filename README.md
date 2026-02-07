# FinAccountingApp

Графическое и веб‑приложение для персонального финансового учёта с мультивалютностью, категориями и отчётами.

## 📋 Оглавление

- [Быстрый старт](#-быстрый-старт)
- [Использование приложения](#️-использование-приложения)
- [Веб-приложение](#-веб-приложение)
- [Архитектура проекта](#️-архитектура-проекта)
- [Программный API](#-программный-api)
- [Файловая структура](#-файловая-структура)
- [Тесты](#-тесты)
- [Поддерживаемые валюты](#-поддерживаемые-валюты)

---

## 🛠️ Недавние улучшения

- Кнопки в главном меню стали вкладками для улучшения пользовательского опыта и навигации, а также сохранения состояния при переключении между вкладками.

## 🚀 Быстрый старт

### Системные требования

- Python 3.10+
- pip

### Установка

```bash
# Перейдите в директорию проекта
cd "Проект ФУ/project"

# Создайте виртуальное окружение
python -m venv .venv

# Активация (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Активация (Windows CMD)
.venv\Scripts\activate.bat

# Активация (Linux/macOS)
source .venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

### Первый запуск

```bash
python main.py
```

После запуска откроется графическое окно приложения Financial Accounting.

---

## 🖥️ Использование приложения

### Главное окно

После запуска `python main.py` откроется окно с вкладками управления и блоком инфографики.

Вкладки и действия:

- `Infographics` — отображение инфографики (круговая диаграмма, гистограммы) с возможностью фильтрации по месяцу/году.
- `Operations` — добавление/удаление записей, установка начального остатка.
- `Reports` — генерация отчётов, экспорт.
- `Settings` — управление обязательными расходами.

Инфографика:

- Круговая диаграмма расходов по категориям с фильтром месяца.
- Гистограмма доходов/расходов по дням месяца.
- Гистограмма доходов/расходов по месяцам года.

Доходы отображаются зелёным, расходы — красным. Для круговой диаграммы малые категории агрегируются в «Прочее». Список категорий в легенде прокручивается.

### Добавление дохода/расхода

1. Откройте вкладку `Operations`.
2. В блоке `Add operation` выберите тип операции (`Income` или `Expense`).
3. Укажите дату в формате `YYYY-MM-DD` (дата не может быть в будущем).
4. Введите сумму.
5. Укажите валюту (по умолчанию `KZT`).
6. Укажите категорию (по умолчанию `General`).
7. Нажмите `Save`.

Сумма конвертируется в базовую валюту `KZT` по текущим курсам сервиса валют.

### Генерация отчёта

1. Откройте вкладку `Reports`.
2. Введите фильтры (опционально):
   - `Period` — префикс даты (например, `2025` или `2025-01`).
   - `Category` — фильтр по категории.
3. Включите опции:
   - `Group by category` — группировка по категориям.
   - `Display as table` — табличный формат.
4. Нажмите `Generate`.

Внизу отображается дополнительная таблица «Monthly Income/Expense Summary» для выбранного года и месяцев.

Экспорт отчёта:

- Форматы: `CSV`, `XLSX`, `PDF`.
- В `XLSX` добавляется лист `Yearly Report` с помесячной сводкой. Также создаётся второй, промежуточный лист `By Category` с группировкой записей по категориям и подсуммами.
- В `PDF` помесячная сводка остаётся, а после основной выписки добавляются таблицы с разбивкой по категориям (каждая категория — отдельная таблица с подсуммой).

### Удаление записи

1. Откройте вкладку `Operations`.
2. В блоке `List of operation` выберите запись из списка.
3. Нажмите `Delete Selected` и подтвердите удаление.

### Установка начального остатка

1. Откройте вкладку `Operations`.
2. Введите сумму (может быть отрицательной).
3. Нажмите `Save`.

Начальный остаток учитывается в итоговом балансе отчётов.

### Управление обязательными расходами

Во вкладке `Settings` доступны операции:

- `Add` — добавить обязательный расход.
- `Delete` — удалить выбранный.
- `Delete All` — удалить все.
- `Add to Report` — добавить выбранный расход в отчёт с указанной датой.
- Селектор формата файла для импорта/экспорта.
- `Import` — импорт обязательных расходов.
- `Export` — экспорт обязательных расходов.

Поля обязательного расхода:

- `Amount`, `Currency`, `Category` (по умолчанию `Mandatory`), `Description` (обязательно), `Period` (`daily`, `weekly`, `monthly`, `yearly`).

Импорт/экспорт обязательных расходов:

- Импорт: `CSV`, `XLSX`.
- Экспорт: `CSV`, `XLSX`, `PDF`.

### Импорт финансовых записей

Импорт выполняется через `Import` во вкладке `Operations`.

Форматы:

- `CSV`, `XLSX`.
- Все существующие записи заменяются данными из файла.

Формат данных:

- Колонки: `Date,Type,Category,Amount (KZT)`.
- `Type`: `Income`, `Expense`, `Mandatory Expense`.
- Допустима строка `Initial Balance` с пустой датой.
- Строки `SUBTOTAL` и `FINAL BALANCE` игнорируются при импорте.

### Хранение данных

Данные хранятся в `records.json` в корне проекта.

Формат:

```json
{
  "initial_balance": 50000.0,
  "records": [
    {
      "type": "income",
      "date": "2025-01-15",
      "amount": 350000.0,
      "category": "Зарплата"
    },
    {
      "type": "expense",
      "date": "2025-01-16",
      "amount": 25000.0,
      "category": "Продукты"
    },
    {
      "type": "mandatory_expense",
      "date": "2025-01-20",
      "amount": 150000.0,
      "category": "Mandatory",
      "description": "Monthly rent",
      "period": "monthly"
    }
  ],
  "mandatory_expenses": [
    {
      "date": "",
      "amount": 150000.0,
      "category": "Mandatory",
      "description": "Monthly rent",
      "period": "monthly"
    }
  ]
}
```

---

## 🌐 Веб-приложение

Веб‑версия находится в `web/` и работает полностью на клиенте (без сервера). Данные хранятся в `localStorage` браузера.

Особенности:

- Отдельные разделы для доходов, расходов, отчётов и настроек.
- Встроенные графики и дашборд.
- Поддержка курсов НБ РК через RSS (`rates_all.xml`) с дневным кэшированием в `localStorage`.
- Экспорт отчёта в `CSV` (веб‑версия).

Запуск: откройте `web/index.html` в браузере.

---

## 🏗️ Архитектура проекта

Проект следует слоистой архитектуре:

- `domain/` — бизнес‑модели и правила (записи, отчёты, валидация дат и периодов, валюты).
- `app/` — сценарии использования (use cases) и адаптер сервиса валют.
- `infrastructure/` — хранилище данных (JSON‑репозиторий).
- `utils/` — импорт/экспорт и подготовка данных для графиков.
- `gui/` — GUI слой (Tkinter).
- `web/` — автономное веб‑приложение.

Поток данных для GUI:

- UI (Tkinter) → `app/use_cases.py` → `infrastructure/repositories.py` → `records.json`.

---

## 📝 Программный API

Ниже — ключевые классы и функции, синхронизированные с актуальным кодом.

### Domain

`domain/records.py`

- `Record` — базовая запись (абстрактный класс).
- `IncomeRecord` — доход.
- `ExpenseRecord` — расход.
- `MandatoryExpenseRecord` — обязательный расход с `description` и `period`.

`domain/currency.py`

- `CurrencyService` — конвертация валют в базовую (`KZT`).

`domain/reports.py`

- `Report(records, initial_balance=0.0)` — отчёт.
- `total()` — итоговый баланс с учётом начального остатка.
- `filter_by_period(prefix)` — фильтрация по префиксу даты.
- `filter_by_category(category)` — фильтрация по категории.
- `grouped_by_category()` — группировка по категориям.
- `monthly_income_expense_rows(year=None, up_to_month=None)` — агрегаты по месяцам.
- `monthly_income_expense_table(year=None, up_to_month=None)` — таблица по месяцам.
- `as_table(summary_mode="full"|"total_only")` — табличный вывод.
- `to_csv(filepath)` и `from_csv(filepath)` — экспорт/импорт CSV.

`domain/validation.py`

- `parse_ymd(value)` — парсинг и валидация даты `YYYY-MM-DD`.
- `ensure_not_future(date)` — запрет будущих дат.
- `ensure_valid_period(period)` — валидация периодов.

### Application

`app/services.py`

- `CurrencyService(rates=None, base="KZT", use_online=False)` — адаптер для доменного сервиса.
- При `use_online=True` пытается загрузить курсы НБ РК и кэширует в `currency_rates.json`.

`app/use_cases.py`

- `CreateIncome.execute(date, amount, currency, category)`.
- `CreateExpense.execute(date, amount, currency, category)`.
- `GenerateReport.execute()` → `Report` с учётом начального остатка.
- `DeleteRecord.execute(index)`.
- `DeleteAllRecords.execute()`.
- `ImportFromCSV.execute(filepath)` — импорт и полная замена записей.
- `CreateMandatoryExpense.execute(amount, currency, category, description, period)`.
- `GetMandatoryExpenses.execute()`.
- `DeleteMandatoryExpense.execute(index)`.
- `DeleteAllMandatoryExpenses.execute()`.
- `AddMandatoryExpenseToReport.execute(index, date)`.

### Infrastructure

`infrastructure/repositories.py`

- `RecordRepository` — интерфейс репозитория.
- `JsonFileRecordRepository(file_path="records.json")` — JSON‑хранилище.

Методы:

- `save(record)`.
- `load_all()`.
- `delete_by_index(index)`.
- `delete_all()`.
- `save_initial_balance(balance)`.
- `load_initial_balance()`.
- `save_mandatory_expense(expense)`.
- `load_mandatory_expenses()`.
- `delete_mandatory_expense_by_index(index)`.
- `delete_all_mandatory_expenses()`.

### GUI

`gui/tkinter_gui.py`

- `FinancialAccountingApp` — основной класс приложения с Tkinter.

Методы:

- `add_income()`.
- `add_expense()`.
- `generate_report()`.
- `delete_record()`.
- `delete_all_records()`.
- `import_from_csv()`.
- `import_from_xlsx()`.
- `set_initial_balance()`.
- `manage_mandatory_expenses()`.

`gui/exporters.py`

- `export_report(report, filepath, fmt)`.
- `export_mandatory_expenses(expenses, filepath, fmt)`.

`gui/importers.py`

- `import_report_from_xlsx(filepath)`
- `import_mandatory_expenses_from_csv(filepath)`
- `import_mandatory_expenses_from_xlsx(filepath)`

`gui/helpers.py`

- `open_in_file_manager(path)`
- `safe_destroy(window)` — безопасное уничтожение окна.
- `safe_focus(window)` — безопасное фокусирование окна.

### Utils

`utils/csv_utils.py`

- `report_to_csv(report, filepath)`.
- `report_from_csv(filepath)`.
- `export_mandatory_expenses_to_csv(expenses, filepath)`.
- `import_mandatory_expenses_from_csv(filepath)`.

`utils/excel_utils.py`

- `report_to_xlsx(report, filepath)`.
- `report_from_xlsx(filepath)`.
- `export_mandatory_expenses_to_xlsx(expenses, filepath)`.
- `import_mandatory_expenses_from_xlsx(filepath)`.

`utils/pdf_utils.py`

- `report_to_pdf(report, filepath)`.
- `export_mandatory_expenses_to_pdf(expenses, filepath)`.

`utils/charting.py`

- `aggregate_expenses_by_category(records)`.
- `aggregate_daily_cashflow(records, year, month)`.
- `aggregate_monthly_cashflow(records, year)`.
- `extract_years(records)`.
- `extract_months(records)`.

---

## 📁 Файловая структура

```
project/
│
├── main.py                     # Точка входа приложения
├── records.json                # Хранилище записей (создаётся автоматически)
├── currency_rates.json         # Кэш курсов валют (use_online=True)
├── requirements.txt            # Python-зависимости
├── pytest.ini                  # Настройки pytest
├── README.md                   # Эта документация
├── README_EN.md                # Документация на английском
├── CHANGELOG.md                # История изменений
├── LICENSE                     # Лицензия
│
├── app/                        # Application layer
│   ├── __init__.py
│   ├── services.py             # CurrencyService адаптер
│   └── use_cases.py            # Use cases
│
├── domain/                     # Domain layer
│   ├── __init__.py
│   ├── records.py              # Записи
│   ├── reports.py              # Отчёты
│   ├── currency.py             # Доменный CurrencyService
│   └── validation.py           # Валидация дат и периодов
│
├── infrastructure/             # Infrastructure layer
│   └── repositories.py         # JSON-репозиторий
│
├── utils/                      # Импорт/экспорт и графики
│   ├── __init__.py
│   ├── csv_utils.py
│   ├── excel_utils.py
│   ├── pdf_utils.py
│   └── charting.py             # Графики и агрегации
│
├── gui/                        # GUI слой (Tkinter)
│   ├── __init__.py
│   ├── tkinter_gui.py          # Основное GUI-приложение
│   ├── exporters.py            # Экспорт отчётов и обязательных расходов
│   ├── importers.py            # Импорт обязательных расходов
│   └── helpers.py              # Помощники для GUI
│
├── web/                        # Веб-приложение
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
└── tests/                      # Тесты
    ├── __init__.py
    ├── test_charting.py
    ├── test_csv.py
    ├── test_currency.py
    ├── test_excel.py
    ├── test_gui_exporters_importers.py
    ├── test_pdf.py
    ├── test_records.py
    ├── test_reports.py
    ├── test_repositories.py
    ├── test_services.py
    ├── test_use_cases.py
    └── test_validation.py
```

---

## 🧪 Тесты

### Запуск

```bash
# Перейти в директорию проекта
cd "Проект ФУ/project"

# Запуск всех тестов
pytest

# С подробным выводом
pytest -v

# Конкретный файл
pytest tests/test_records.py -v

# Конкретный тест
pytest tests/test_reports.py::test_report_total -v
```

### Покрытие

```bash
pip install pytest-cov
pytest --cov=. --cov-report=term-missing
pytest --cov=. --cov-report=html
```

> **Примечание:** тесты ожидают, что `CurrencyService` по умолчанию использует локальные курсы (параметр `use_online=False`).

---

## 💱 Поддерживаемые валюты

Дефолтные курсы приложения:

| Валюта              | Код | Дефолтный курс | Описание        |
| ------------------- | --- | -------------- | --------------- |
| Казахстанский тенге | KZT | 1.0            | Базовая валюта  |
| Доллар США          | USD | 500.0          | 1 USD = 500 KZT |
| Евро                | EUR | 590.0          | 1 EUR = 590 KZT |
| Российский рубль    | RUB | 6.5            | 1 RUB = 6.5 KZT |

Если создать `CurrencyService(use_online=True)`, то курсы будут загружены с НБ РК и сохранены в `currency_rates.json`.

---

## 📄 Лицензия

MIT License — свободное использование, модификация и распространение.
