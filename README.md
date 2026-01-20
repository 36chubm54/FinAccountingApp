# FinAccountingApp

Приложение для финансового учёта, позволяющее отслеживать доходы и расходы с поддержкой мультивалютности и генерацией отчётов.

## 📋 Содержание

- [Архитектура](#архитектура)
- [Установка](#установка)
- [Использование CLI](#использование-cli)
- [Примеры кода](#примеры-кода)
- [Структура проекта](#структура-проекта)
- [Тестирование](#тестирование)

## 🏗️ Архитектура

Приложение построено по принципам **Clean Architecture** с разделением на слои:

```
┌─────────────────────────────────────────────────────────────┐
│                        app.py (CLI)                         │
├─────────────────────────────────────────────────────────────┤
│                    app/ (Application Layer)                 │
│              use_cases.py  │  services.py                   │
├─────────────────────────────────────────────────────────────┤
│                    domain/ (Domain Layer)                   │
│         records.py  │  reports.py  │  currency.py           │
├─────────────────────────────────────────────────────────────┤
│               infrastructure/ (Infrastructure Layer)        │
│                      repositories.py                        │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Установка

### Требования
- Python 3.10+
- pip

### Шаги установки

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd project

# Создайте виртуальное окружение
python -m venv .venv

# Активируйте окружение
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

## 💻 Использование CLI

### Добавление дохода

```bash
python app.py add-income --date 2025-03-15 --amount 150000 --currency KZT --category Зарплата
```

**Вывод:**
```
Added income: 150000.0 KZT on 2025-03-15 (category: Зарплата)
```

### Добавление расхода

```bash
python app.py add-expense --date 2025-03-16 --amount 50 --currency USD --category Продукты
```

**Вывод:**
```
Added expense: 50.0 USD on 2025-03-16 (category: Продукты)
```

> **Примечание:** Все суммы автоматически конвертируются в KZT по текущему курсу.

### Генерация отчёта

#### Общий итог
```bash
python app.py report
```

**Вывод:**
```
Total: 125000.00 KZT
```

#### Отчёт в виде таблицы
```bash
python app.py report --table
```

**Вывод:**
```
+------------+---------+----------+--------------+
|    Date    |  Type   | Category | Amount (KZT) |
+------------+---------+----------+--------------+
| 2025-03-15 | Income  | Зарплата |   150000.00  |
| 2025-03-16 | Expense | Продукты |    25000.00  |
+------------+---------+----------+--------------+
|   TOTAL    |         |          |   125000.00  |
+------------+---------+----------+--------------+
```

#### Фильтрация по периоду
```bash
python app.py report --period 2025-03 --table
```

#### Фильтрация по категории
```bash
python app.py report --category Зарплата
```

#### Группировка по категориям
```bash
python app.py report --group-by-category
```

**Вывод:**
```
Report grouped by category:
  Зарплата: 150000.00 KZT
  Продукты: -25000.00 KZT
```

### Удаление записи

```bash
python app.py delete
```

**Интерактивный вывод:**
```
Current records:
[0] 2025-03-15 - Income - Зарплата - 150000.00 KZT
[1] 2025-03-16 - Expense - Продукты - 25000.00 KZT

Enter the index of the record to delete (or 'cancel' to abort): 1
Successfully deleted record at index 1.
```

## 📝 Примеры кода

### Доменные модели (domain/records.py)

Записи о доходах и расходах представлены как неизменяемые dataclass-объекты:

```python
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass(frozen=True)
class Record(ABC):
    date: str      # Дата в формате YYYY-MM-DD
    amount: float  # Сумма в KZT
    category: str  # Категория записи

    @abstractmethod
    def signed_amount(self) -> float:
        """Возвращает сумму со знаком (+ для дохода, - для расхода)"""
        pass


class IncomeRecord(Record):
    """Запись о доходе"""
    def signed_amount(self) -> float:
        return self.amount  # Положительное значение


class ExpenseRecord(Record):
    """Запись о расходе"""
    def signed_amount(self) -> float:
        return -abs(self.amount)  # Отрицательное значение
```

**Пример использования:**

```python
from domain.records import IncomeRecord, ExpenseRecord

# Создание записи о доходе
income = IncomeRecord(date="2025-03-15", amount=150000.0, category="Зарплата")
print(income.signed_amount())  # 150000.0

# Создание записи о расходе
expense = ExpenseRecord(date="2025-03-16", amount=25000.0, category="Продукты")
print(expense.signed_amount())  # -25000.0
```

### Сервис валют (domain/currency.py)

Конвертация валют в базовую валюту (KZT):

```python
class CurrencyService:
    def __init__(self, rates: dict[str, float], base: str = "KZT"):
        self._rates = rates  # Курсы валют к базовой
        self._base = base    # Базовая валюта

    def convert(self, amount: float, currency: str) -> float:
        """Конвертирует сумму в базовую валюту"""
        if currency == self._base:
            return amount
        return amount * self._rates[currency]
```

**Пример использования:**

```python
from domain.currency import CurrencyService

# Создание сервиса с курсами
rates = {"USD": 500.0, "EUR": 590.0, "RUB": 6.5}
currency_service = CurrencyService(rates=rates, base="KZT")

# Конвертация 100 USD в KZT
amount_kzt = currency_service.convert(100, "USD")
print(f"100 USD = {amount_kzt} KZT")  # 100 USD = 50000.0 KZT

# KZT остаётся без изменений
amount_kzt = currency_service.convert(10000, "KZT")
print(f"10000 KZT = {amount_kzt} KZT")  # 10000 KZT = 10000 KZT
```

### Отчёты (domain/reports.py)

Класс `Report` предоставляет методы для анализа записей:

```python
from domain.reports import Report
from domain.records import IncomeRecord, ExpenseRecord

# Создание записей
records = [
    IncomeRecord(date="2025-03-15", amount=150000.0, category="Зарплата"),
    ExpenseRecord(date="2025-03-16", amount=25000.0, category="Продукты"),
    ExpenseRecord(date="2025-03-17", amount=5000.0, category="Транспорт"),
    IncomeRecord(date="2025-04-01", amount=10000.0, category="Подработка"),
]

# Создание отчёта
report = Report(records)

# Общий итог
print(f"Итого: {report.total():.2f} KZT")  # Итого: 130000.00 KZT

# Фильтрация по периоду (март 2025)
march_report = report.filter_by_period("2025-03")
print(f"Март: {march_report.total():.2f} KZT")  # Март: 120000.00 KZT

# Фильтрация по категории
salary_report = report.filter_by_category("Зарплата")
print(f"Зарплата: {salary_report.total():.2f} KZT")  # Зарплата: 150000.00 KZT

# Группировка по категориям
groups = report.grouped_by_category()
for category, cat_report in groups.items():
    print(f"{category}: {cat_report.total():.2f} KZT")

# Вывод в виде таблицы
print(report.as_table())
```

### Репозиторий (infrastructure/repositories.py)

Сохранение и загрузка записей из JSON-файла:

```python
from infrastructure.repositories import JsonFileRecordRepository
from domain.records import IncomeRecord, ExpenseRecord

# Создание репозитория
repo = JsonFileRecordRepository(file_path="my_records.json")

# Сохранение записей
income = IncomeRecord(date="2025-03-15", amount=150000.0, category="Зарплата")
repo.save(income)

expense = ExpenseRecord(date="2025-03-16", amount=25000.0, category="Продукты")
repo.save(expense)

# Загрузка всех записей
all_records = repo.load_all()
for record in all_records:
    print(f"{record.date}: {record.amount} ({record.category})")

# Удаление записи по индексу
deleted = repo.delete_by_index(0)
print(f"Удалено: {deleted}")  # Удалено: True
```

**Формат JSON-файла (records.json):**

```json
[
  {
    "type": "income",
    "date": "2025-03-15",
    "amount": 150000.0,
    "category": "Зарплата"
  },
  {
    "type": "expense",
    "date": "2025-03-16",
    "amount": 25000.0,
    "category": "Продукты"
  }
]
```

### Use Cases (app/use_cases.py)

Бизнес-логика приложения инкапсулирована в use case классах:

```python
from infrastructure.repositories import JsonFileRecordRepository
from app.services import CurrencyService
from app.use_cases import CreateIncome, CreateExpense, GenerateReport, DeleteRecord

# Инициализация зависимостей
repository = JsonFileRecordRepository()
currency = CurrencyService()

# Добавление дохода
create_income = CreateIncome(repository, currency)
create_income.execute(
    date="2025-03-15",
    amount=300,           # 300 USD
    currency="USD",       # Будет конвертировано в KZT
    category="Фриланс"
)

# Добавление расхода
create_expense = CreateExpense(repository, currency)
create_expense.execute(
    date="2025-03-16",
    amount=50,
    currency="EUR",
    category="Развлечения"
)

# Генерация отчёта
generate_report = GenerateReport(repository)
report = generate_report.execute()
print(f"Итого: {report.total():.2f} KZT")

# Удаление записи
delete_record = DeleteRecord(repository)
success = delete_record.execute(index=0)
print(f"Удалено: {success}")
```

### Сервис валют с онлайн-курсами (app/services.py)

Приложение поддерживает получение актуальных курсов с сайта Национального Банка РК:

```python
from app.services import CurrencyService

# Использование дефолтных курсов (для тестов)
currency = CurrencyService()
print(currency.convert(100, "USD"))  # 50000.0 (100 * 500)

# Использование онлайн-курсов с кэшированием
currency_online = CurrencyService(use_online=True)
print(currency_online.convert(100, "USD"))  # Актуальный курс

# Использование кастомных курсов
custom_rates = {"USD": 450.0, "EUR": 520.0}
currency_custom = CurrencyService(rates=custom_rates)
print(currency_custom.convert(100, "USD"))  # 45000.0
```

## 📁 Структура проекта

```
project/
├── app.py                    # Точка входа CLI
├── records.json              # Хранилище записей
├── currency_rates.json       # Кэш курсов валют
├── requirements.txt          # Зависимости Python
├── README.md                 # Документация
│
├── app/                      # Слой приложения
│   ├── __init__.py
│   ├── services.py           # Сервисы (CurrencyService адаптер)
│   └── use_cases.py          # Use cases (CreateIncome, CreateExpense, etc.)
│
├── domain/                   # Доменный слой
│   ├── __init__.py
│   ├── records.py            # Доменные модели (Record, IncomeRecord, ExpenseRecord)
│   ├── reports.py            # Отчёты (Report)
│   └── currency.py           # Сервис валют (CurrencyService)
│
├── infrastructure/           # Инфраструктурный слой
│   └── repositories.py       # Репозитории (JsonFileRecordRepository)
│
└── tests/                    # Тесты
    ├── __init__.py
    ├── test_currency.py
    ├── test_records.py
    ├── test_reports.py
    ├── test_repositories.py
    ├── test_services.py
    └── test_use_cases.py
```

## 🧪 Тестирование

Запуск всех тестов:

```bash
cd project
pytest
```

Запуск с подробным выводом:

```bash
pytest -v
```

Запуск конкретного теста:

```bash
pytest tests/test_records.py -v
```

Запуск с покрытием кода:

```bash
pip install pytest-cov
pytest --cov=. --cov-report=html
```

## 📊 Поддерживаемые валюты

| Валюта | Код | Дефолтный курс к KZT |
|--------|-----|---------------------|
| Тенге  | KZT | 1.0 (базовая)       |
| Доллар | USD | 500.0               |
| Евро   | EUR | 590.0               |
| Рубль  | RUB | 6.5                 |

> При использовании `use_online=True` курсы загружаются с сайта [Национального Банка РК](https://nationalbank.kz/ru/exchangerates/ezhednevnye-oficialnye-rynochnye-kursy-valyut/).

## 📄 Лицензия

MIT License
