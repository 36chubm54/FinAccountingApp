// Финансовое приложение - JavaScript логика

// Хранилище данных (localStorage)
const STORAGE_KEY = 'financial_records';
const SETTINGS_KEY = 'financial_settings';
const RATES_KEY = 'currency_rates';
const RATES_TIMESTAMP_KEY = 'currency_rates_timestamp';

// URL для получения курсов валют Национального банка Казахстана
const EXCHANGE_RATES_URL = 'https://nationalbank.kz/ru/exchangerates/ezhednevnye-oficialnye-rynochnye-kursy-valyut/';
const EXCHANGE_RATES_API = 'https://nationalbank.kz/rss/rates_all.xml';

// Символы валют
const currencySymbols = {
    'KZT': '₸',
    'USD': '$',
    'EUR': '€',
    'RUB': '₽'
};

function clearElement(element) {
    while (element.firstChild) {
        element.removeChild(element.firstChild);
    }
}

function createElement(tag, className, text) {
    const el = document.createElement(tag);
    if (className) {
        el.className = className;
    }
    if (text !== undefined) {
        el.textContent = text;
    }
    return el;
}

// Курсы валют (по умолчанию, будут обновлены с API)
let exchangeRates = {
    'KZT': 1,
    'USD': 500,
    'EUR': 590,
    'RUB': 6.5
};

// Загрузка курсов валют из localStorage или API
async function loadExchangeRates() {
    // Проверяем, есть ли сохранённые курсы и не устарели ли они (обновляем раз в день)
    const savedRates = localStorage.getItem(RATES_KEY);
    const savedTimestamp = localStorage.getItem(RATES_TIMESTAMP_KEY);
    const now = Date.now();
    const oneDay = 24 * 60 * 60 * 1000; // 24 часа в миллисекундах
    
    if (savedRates && savedTimestamp && (now - parseInt(savedTimestamp)) < oneDay) {
        // Используем сохранённые курсы
        exchangeRates = JSON.parse(savedRates);
        console.log('Курсы валют загружены из кэша:', exchangeRates);
        updateRatesDisplay();
        return;
    }
    
    // Загружаем новые курсы с API
    await fetchExchangeRates();
}

// Получение курсов валют с API Национального банка Казахстана
async function fetchExchangeRates() {
    try {
        showToast('Загрузка курсов валют...', 'info');
        
        // Используем CORS proxy для обхода ограничений браузера
        // В продакшене лучше использовать собственный backend
        const proxyUrl = 'https://api.allorigins.win/raw?url=';
        const response = await fetch(proxyUrl + encodeURIComponent(EXCHANGE_RATES_API));
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const xmlText = await response.text();
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
        
        // Парсим XML и извлекаем курсы
        const items = xmlDoc.querySelectorAll('item');
        const newRates = { 'KZT': 1 };
        
        items.forEach(item => {
            const title = item.querySelector('title')?.textContent;
            const description = item.querySelector('description')?.textContent;
            
            if (title && description) {
                const rate = parseFloat(description);
                if (!isNaN(rate)) {
                    // Курс показывает сколько тенге за единицу валюты
                    newRates[title] = rate;
                }
            }
        });
        
        // Проверяем, что получили нужные валюты
        if (newRates['USD'] && newRates['EUR'] && newRates['RUB']) {
            exchangeRates = newRates;
            
            // Сохраняем в localStorage
            localStorage.setItem(RATES_KEY, JSON.stringify(exchangeRates));
            localStorage.setItem(RATES_TIMESTAMP_KEY, Date.now().toString());
            
            console.log('Курсы валют обновлены с НБ РК:', exchangeRates);
            showToast('Курсы валют обновлены', 'success');
            updateRatesDisplay();
            refreshAllData();
        } else {
            throw new Error('Не удалось получить все необходимые курсы');
        }
        
    } catch (error) {
        console.error('Ошибка загрузки курсов валют:', error);
        showToast('Не удалось загрузить курсы валют. Используются кэшированные данные.', 'error');
        
        // Пробуем загрузить из localStorage даже если они устарели
        const savedRates = localStorage.getItem(RATES_KEY);
        if (savedRates) {
            exchangeRates = JSON.parse(savedRates);
        }
        updateRatesDisplay();
    }
}

// Принудительное обновление курсов валют
async function refreshExchangeRates() {
    // Очищаем timestamp чтобы принудительно обновить
    localStorage.removeItem(RATES_TIMESTAMP_KEY);
    await fetchExchangeRates();
}

// Обновление отображения курсов валют в интерфейсе
function updateRatesDisplay() {
    const ratesContainer = document.getElementById('rates-display');
    if (!ratesContainer) {
        return;
    }

    clearElement(ratesContainer);

    const timestamp = localStorage.getItem(RATES_TIMESTAMP_KEY);
    const date = timestamp ? new Date(parseInt(timestamp)).toLocaleDateString('ru-RU') : 'Н/Д';

    const info = createElement('div', 'rates-info');
    info.appendChild(createElement('span', 'rates-title', `Курсы НБ РК (${date}):`));
    info.appendChild(
        createElement(
            'span',
            'rate-item',
            `USD: ${exchangeRates['USD']?.toFixed(2) || 'Н/Д'} ₸`
        )
    );
    info.appendChild(
        createElement(
            'span',
            'rate-item',
            `EUR: ${exchangeRates['EUR']?.toFixed(2) || 'Н/Д'} ₸`
        )
    );
    info.appendChild(
        createElement(
            'span',
            'rate-item',
            `RUB: ${exchangeRates['RUB']?.toFixed(2) || 'Н/Д'} ₸`
        )
    );

    const refreshButton = createElement('button', 'btn-refresh-rates', '🔄');
    refreshButton.title = 'Обновить курсы';
    refreshButton.type = 'button';
    refreshButton.addEventListener('click', refreshExchangeRates);
    info.appendChild(refreshButton);

    ratesContainer.appendChild(info);
}

// Получить текущий курс валюты
function getExchangeRate(currency) {
    return exchangeRates[currency] || 1;
}

// Конвертация суммы из одной валюты в другую
function convertCurrency(amount, fromCurrency, toCurrency) {
    try {
        const fromRate = getExchangeRate(fromCurrency);
        const toRate = getExchangeRate(toCurrency);
        if (toRate === 0) {
            throw new Error("Invalid target currency rate");
        }
        const amountInKZT = amount * fromRate;
        return amountInKZT / toRate;
    } catch (error) {
        console.error("Currency conversion error:", error);
        showToast("Ошибка конвертации валюты", "error");
        return amount; // Return original amount on error
    }
}

// Инициализация приложения
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    // Установка текущей даты
    updateCurrentDate();
    
    // Загрузка настроек
    loadSettings();
    
    // Загрузка курсов валют
    await loadExchangeRates();
    
    // Инициализация навигации
    initNavigation();
    
    // Загрузка и отображение данных
    refreshAllData();
    
    // Установка даты по умолчанию в форме
    document.getElementById('record-date').valueAsDate = new Date();
    
    // Обновление списка категорий в фильтрах
    updateCategoryFilter();
}

// Обновление текущей даты
function updateCurrentDate() {
    const dateElement = document.getElementById('current-date');
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    dateElement.textContent = new Date().toLocaleDateString('ru-RU', options);
}

// Инициализация навигации
function initNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const sectionId = btn.dataset.section;
            
            // Обновление активной кнопки
            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Обновление активной секции
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.getElementById(sectionId).classList.add('active');
            
            // Обновление заголовка
            const titles = {
                'dashboard': 'Обзор',
                'income': 'Доходы',
                'expenses': 'Расходы',
                'reports': 'Отчёты',
                'settings': 'Настройки'
            };
            document.getElementById('section-title').textContent = titles[sectionId];
        });
    });
}

// Работа с данными
function getRecords() {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
}

function saveRecords(records) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
}

function addRecord(record) {
    const records = getRecords();
    record.id = Date.now();
    records.push(record);
    saveRecords(records);
    return record;
}

function deleteRecordById(id) {
    let records = getRecords();
    records = records.filter(r => r.id !== id);
    saveRecords(records);
}

// Модальное окно
function openModal(type) {
    const modal = document.getElementById('record-modal');
    const title = document.getElementById('modal-title');
    const typeInput = document.getElementById('record-type');
    
    typeInput.value = type;
    title.textContent = type === 'income' ? 'Добавить доход' : 'Добавить расход';
    
    modal.classList.add('active');
}

function closeModal() {
    const modal = document.getElementById('record-modal');
    modal.classList.remove('active');
    document.getElementById('record-form').reset();
    document.getElementById('record-date').valueAsDate = new Date();
}

// Сохранение записи
function saveRecord(event) {
    event.preventDefault();
    
    const type = document.getElementById('record-type').value;
    const date = document.getElementById('record-date').value;
    const amount = parseFloat(document.getElementById('record-amount').value);
    const currency = document.getElementById('record-currency').value;
    const category = document.getElementById('record-category').value;
    
    if (!date || !amount || !category) {
        showToast('Заполните все поля', 'error');
        return;
    }
    
    const record = {
        type,
        date,
        amount,
        currency,
        category
    };
    
    addRecord(record);
    closeModal();
    refreshAllData();
    showToast(`${type === 'income' ? 'Доход' : 'Расход'} успешно добавлен`, 'success');
}

// Удаление записи
function deleteRecord(id) {
    if (confirm('Вы уверены, что хотите удалить эту запись?')) {
        deleteRecordById(id);
        refreshAllData();
        showToast('Запись удалена', 'info');
    }
}

// Обновление всех данных
function refreshAllData() {
    updateDashboard();
    updateIncomeTable();
    updateExpensesTable();
    updateCategoryFilter();
}

// Обновление дашборда
function updateDashboard() {
    const records = getRecords();
    const selectedCurrency = document.getElementById('currency-select').value;
    
    let totalIncome = 0;
    let totalExpenses = 0;
    
    records.forEach(record => {
        const amountInKZT = record.amount * exchangeRates[record.currency];
        const amountInSelected = amountInKZT / exchangeRates[selectedCurrency];
        
        if (record.type === 'income') {
            totalIncome += amountInSelected;
        } else {
            totalExpenses += amountInSelected;
        }
    });
    
    const balance = totalIncome - totalExpenses;
    const symbol = currencySymbols[selectedCurrency];
    
    document.getElementById('total-income').textContent = formatNumber(totalIncome) + ' ' + symbol;
    document.getElementById('total-expenses').textContent = formatNumber(totalExpenses) + ' ' + symbol;
    document.getElementById('total-balance').textContent = formatNumber(balance) + ' ' + symbol;
    
    // Обновление последних транзакций
    updateRecentTransactions(records);
}

// Обновление последних транзакций
function updateRecentTransactions(records) {
    const container = document.getElementById('recent-list');
    
    if (records.length === 0) {
        clearElement(container);
        const emptyState = createElement('div', 'empty-state');
        emptyState.appendChild(createElement('div', 'icon', '📝'));
        emptyState.appendChild(createElement('p', null, 'Нет записей. Добавьте первую транзакцию!'));
        container.appendChild(emptyState);
        return;
    }
    
    // Сортировка по дате (новые сверху) и взятие последних 5
    const recentRecords = [...records]
        .sort((a, b) => new Date(b.date) - new Date(a.date))
        .slice(0, 5);
    
    clearElement(container);
    recentRecords.forEach(record => {
        const symbol = currencySymbols[record.currency];
        const isIncome = record.type === 'income';

        const item = createElement('div', 'transaction-item');
        const info = createElement('div', 'transaction-info');
        const icon = createElement('div', `transaction-icon ${record.type}`, isIncome ? '💵' : '💸');
        const details = createElement('div', 'transaction-details');
        details.appendChild(createElement('span', 'transaction-category', record.category));
        details.appendChild(createElement('span', 'transaction-date', formatDate(record.date)));
        info.appendChild(icon);
        info.appendChild(details);
        item.appendChild(info);

        const amount = createElement(
            'span',
            `transaction-amount ${record.type}`,
            `${isIncome ? '+' : '-'}${formatNumber(record.amount)} ${symbol}`
        );
        item.appendChild(amount);

        container.appendChild(item);
    });
}

// Обновление таблицы доходов
function updateIncomeTable() {
    const records = getRecords().filter(r => r.type === 'income');
    const tbody = document.getElementById('income-table-body');
    
    if (records.length === 0) {
        clearElement(tbody);
        const tr = document.createElement('tr');
        const td = createElement('td', 'empty-state');
        td.colSpan = 5;
        td.appendChild(createElement('p', null, 'Нет записей о доходах'));
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }
    
    clearElement(tbody);
    records
        .sort((a, b) => new Date(b.date) - new Date(a.date))
        .forEach(record => {
            const symbol = currencySymbols[record.currency];
            const tr = document.createElement('tr');

            tr.appendChild(createElement('td', null, formatDate(record.date)));
            tr.appendChild(createElement('td', null, record.category));

            const amountTd = createElement(
                'td',
                null,
                `+${formatNumber(record.amount)} ${symbol}`
            );
            amountTd.style.color = 'var(--success-color)';
            amountTd.style.fontWeight = '600';
            tr.appendChild(amountTd);

            tr.appendChild(createElement('td', null, record.currency));

            const actionTd = document.createElement('td');
            const button = createElement('button', 'action-btn delete', 'Удалить');
            button.type = 'button';
            button.addEventListener('click', () => deleteRecord(record.id));
            actionTd.appendChild(button);
            tr.appendChild(actionTd);

            tbody.appendChild(tr);
        });
}

// Обновление таблицы расходов
function updateExpensesTable() {
    const records = getRecords().filter(r => r.type === 'expense');
    const tbody = document.getElementById('expenses-table-body');
    
    if (records.length === 0) {
        clearElement(tbody);
        const tr = document.createElement('tr');
        const td = createElement('td', 'empty-state');
        td.colSpan = 5;
        td.appendChild(createElement('p', null, 'Нет записей о расходах'));
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }
    
    clearElement(tbody);
    records
        .sort((a, b) => new Date(b.date) - new Date(a.date))
        .forEach(record => {
            const symbol = currencySymbols[record.currency];
            const tr = document.createElement('tr');

            tr.appendChild(createElement('td', null, formatDate(record.date)));
            tr.appendChild(createElement('td', null, record.category));

            const amountTd = createElement(
                'td',
                null,
                `-${formatNumber(record.amount)} ${symbol}`
            );
            amountTd.style.color = 'var(--danger-color)';
            amountTd.style.fontWeight = '600';
            tr.appendChild(amountTd);

            tr.appendChild(createElement('td', null, record.currency));

            const actionTd = document.createElement('td');
            const button = createElement('button', 'action-btn delete', 'Удалить');
            button.type = 'button';
            button.addEventListener('click', () => deleteRecord(record.id));
            actionTd.appendChild(button);
            tr.appendChild(actionTd);

            tbody.appendChild(tr);
        });
}

// Обновление фильтра категорий
function updateCategoryFilter() {
    const records = getRecords();
    const categories = [...new Set(records.map(r => r.category))];
    const select = document.getElementById('report-category');
    
    clearElement(select);
    const firstOption = document.createElement('option');
    firstOption.value = '';
    firstOption.textContent = 'Все категории';
    select.appendChild(firstOption);

    categories.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat;
        option.textContent = cat;
        select.appendChild(option);
    });
}

// Генерация отчёта
function generateReport() {
    const records = getRecords();
    const period = document.getElementById('report-period').value;
    const category = document.getElementById('report-category').value;
    const groupByCategory = document.getElementById('group-by-category').checked;
    const resultContainer = document.getElementById('report-result');
    
    let filteredRecords = [...records];
    
    // Фильтрация по периоду
    if (period) {
        filteredRecords = filteredRecords.filter(r => r.date.startsWith(period));
    }
    
    // Фильтрация по категории
    if (category) {
        filteredRecords = filteredRecords.filter(r => r.category === category);
    }
    
    if (filteredRecords.length === 0) {
        clearElement(resultContainer);
        const emptyState = createElement('div', 'empty-state');
        emptyState.appendChild(createElement('div', 'icon', '📊'));
        emptyState.appendChild(createElement('p', null, 'Нет данных для отображения'));
        resultContainer.appendChild(emptyState);
        return;
    }
    
    if (groupByCategory) {
        // Группировка по категориям
        const grouped = {};
        filteredRecords.forEach(r => {
            if (!grouped[r.category]) {
                grouped[r.category] = { income: 0, expense: 0, records: [] };
            }
            const amountInKZT = r.amount * exchangeRates[r.currency];
            if (r.type === 'income') {
                grouped[r.category].income += amountInKZT;
            } else {
                grouped[r.category].expense += amountInKZT;
            }
            grouped[r.category].records.push(r);
        });
        
        clearElement(resultContainer);
        const wrapper = createElement('div', 'report-grouped');
        for (const [cat, data] of Object.entries(grouped)) {
            const balance = data.income - data.expense;
            const block = createElement('div', 'report-category-block');
            block.style.marginBottom = '20px';
            block.style.padding = '16px';
            block.style.background = 'var(--bg-color)';
            block.style.borderRadius = '8px';

            const title = createElement('h4', null, cat);
            title.style.marginBottom = '10px';
            block.appendChild(title);

            const income = createElement('p', null, `Доходы: ${formatNumber(data.income)} ₸`);
            income.style.color = 'var(--success-color)';
            block.appendChild(income);

            const expense = createElement('p', null, `Расходы: ${formatNumber(data.expense)} ₸`);
            expense.style.color = 'var(--danger-color)';
            block.appendChild(expense);

            const balanceEl = createElement('p', null, `Баланс: ${formatNumber(balance)} ₸`);
            balanceEl.style.fontWeight = '600';
            block.appendChild(balanceEl);

            wrapper.appendChild(block);
        }
        resultContainer.appendChild(wrapper);
    } else {
        // Общая таблица
        let totalIncome = 0;
        let totalExpense = 0;

        clearElement(resultContainer);
        const table = document.createElement('table');
        table.style.width = '100%';

        const thead = document.createElement('thead');
        const headRow = document.createElement('tr');
        ['Дата', 'Тип', 'Категория', 'Сумма'].forEach(text => {
            headRow.appendChild(createElement('th', null, text));
        });
        thead.appendChild(headRow);
        table.appendChild(thead);

        const tbody = document.createElement('tbody');
        filteredRecords
            .sort((a, b) => new Date(b.date) - new Date(a.date))
            .forEach(r => {
                const symbol = currencySymbols[r.currency];
                const amountInKZT = r.amount * exchangeRates[r.currency];

                if (r.type === 'income') {
                    totalIncome += amountInKZT;
                } else {
                    totalExpense += amountInKZT;
                }

                const tr = document.createElement('tr');
                tr.appendChild(createElement('td', null, formatDate(r.date)));
                tr.appendChild(createElement('td', null, r.type === 'income' ? 'Доход' : 'Расход'));
                tr.appendChild(createElement('td', null, r.category));

                const amountTd = createElement(
                    'td',
                    null,
                    `${r.type === 'income' ? '+' : '-'}${formatNumber(r.amount)} ${symbol}`
                );
                amountTd.style.color =
                    r.type === 'income' ? 'var(--success-color)' : 'var(--danger-color)';
                amountTd.style.fontWeight = '600';
                tr.appendChild(amountTd);

                tbody.appendChild(tr);
            });
        table.appendChild(tbody);
        resultContainer.appendChild(table);

        const summary = createElement('div', null);
        summary.style.marginTop = '20px';
        summary.style.padding = '16px';
        summary.style.background = 'var(--bg-color)';
        summary.style.borderRadius = '8px';

        const totalIncomeEl = createElement(
            'p',
            null,
            `Всего доходов: ${formatNumber(totalIncome)} ₸`
        );
        totalIncomeEl.style.color = 'var(--success-color)';
        summary.appendChild(totalIncomeEl);

        const totalExpenseEl = createElement(
            'p',
            null,
            `Всего расходов: ${formatNumber(totalExpense)} ₸`
        );
        totalExpenseEl.style.color = 'var(--danger-color)';
        summary.appendChild(totalExpenseEl);

        const totalEl = createElement(
            'p',
            null,
            `Итого: ${formatNumber(totalIncome - totalExpense)} ₸`
        );
        totalEl.style.fontWeight = '700';
        totalEl.style.fontSize = '1.2rem';
        summary.appendChild(totalEl);

        resultContainer.appendChild(summary);
    }
    
    showToast('Отчёт сформирован', 'success');
}

// Экспорт в CSV
function exportCSV() {
    const records = getRecords();
    
    if (records.length === 0) {
        showToast('Нет данных для экспорта', 'error');
        return;
    }
    
    const period = document.getElementById('report-period').value;
    const category = document.getElementById('report-category').value;
    
    let filteredRecords = [...records];
    
    if (period) {
        filteredRecords = filteredRecords.filter(r => r.date.startsWith(period));
    }
    
    if (category) {
        filteredRecords = filteredRecords.filter(r => r.category === category);
    }
    
    if (filteredRecords.length === 0) {
        showToast('Нет данных для экспорта с выбранными фильтрами', 'error');
        return;
    }
    
    // Создание CSV
    const headers = ['Дата', 'Тип', 'Категория', 'Сумма', 'Валюта'];
    const rows = filteredRecords.map(r => [
        r.date,
        r.type === 'income' ? 'Доход' : 'Расход',
        r.category,
        r.amount,
        r.currency
    ]);
    
    const csvContent = [
        headers.map(csvEscape).join(','),
        ...rows.map(row => row.map(csvEscape).join(','))
    ].join('\n');
    
    // Скачивание файла
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `financial_report_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    
    showToast('Отчёт экспортирован в CSV', 'success');
}

// Настройки
function loadSettings() {
    const settings = localStorage.getItem(SETTINGS_KEY);
    if (settings) {
        const parsed = JSON.parse(settings);
        
        if (parsed.theme) {
            document.documentElement.setAttribute('data-theme', parsed.theme);
            document.getElementById('theme-select').value = parsed.theme;
        }
        
        if (parsed.defaultCurrency) {
            document.getElementById('default-currency').value = parsed.defaultCurrency;
            document.getElementById('currency-select').value = parsed.defaultCurrency;
        }
    }
}

function saveSettings() {
    const settings = {
        theme: document.getElementById('theme-select').value,
        defaultCurrency: document.getElementById('default-currency').value
    };
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
}

function toggleTheme() {
    const theme = document.getElementById('theme-select').value;
    document.documentElement.setAttribute('data-theme', theme);
    saveSettings();
    showToast(`Тема изменена на ${theme === 'dark' ? 'тёмную' : 'светлую'}`, 'info');
}

function clearAllData() {
    if (confirm('Вы уверены, что хотите удалить ВСЕ данные? Это действие необратимо!')) {
        localStorage.removeItem(STORAGE_KEY);
        refreshAllData();
        showToast('Все данные удалены', 'info');
    }
}

// Вспомогательные функции
function formatNumber(num) {
    return num.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' });
}

function csvEscape(value) {
    const str = String(value ?? '');
    if (/[",\n\r]/.test(str)) {
        return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
}

// Уведомления
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Обработчик изменения валюты
document.getElementById('currency-select').addEventListener('change', updateDashboard);

// Закрытие модального окна при клике вне его
document.getElementById('record-modal').addEventListener('click', (e) => {
    if (e.target.id === 'record-modal') {
        closeModal();
    }
});

// Закрытие модального окна по Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeModal();
    }
});
