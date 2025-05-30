# Настройка Google Sheets API

## Шаги для получения доступа:

### 1. Создайте проект в Google Cloud Console
1. Перейдите на https://console.cloud.google.com/
2. Создайте новый проект или выберите существующий
3. Название проекта: "Price List Analyzer"

### 2. Включите Google Sheets API
1. В левом меню найдите "API и сервисы" → "Библиотека"
2. Найдите "Google Sheets API" 
3. Нажмите "Включить"

### 3. Создайте Service Account
1. Перейдите в "API и сервисы" → "Учетные данные"
2. Нажмите "Создать учетные данные" → "Аккаунт службы"
3. Заполните:
   - Название: price-list-analyzer
   - Описание: Service account for price list analysis
4. Нажмите "Создать и продолжить"
5. Роль: "Редактор" (Editor)
6. Нажмите "Готово"

### 4. Создайте JSON ключ
1. В списке аккаунтов службы найдите созданный аккаунт
2. Нажмите на него
3. Перейдите на вкладку "Ключи"
4. Нажмите "Добавить ключ" → "Создать новый ключ"
5. Выберите тип "JSON"
6. Скачайте файл (например: price-list-analyzer-abc123.json)

### 5. Поместите JSON файл в проект
Сохраните скачанный файл как:
`/Users/denisdomashenko/price_list_analyzer/google_credentials.json`

### 6. Создайте Google Sheet
1. Откройте https://sheets.google.com/
2. Создайте новую таблицу
3. Назовите её "Price List Master Table"
4. Скопируйте ID таблицы из URL (длинная строка между /d/ и /edit)
   Пример URL: https://docs.google.com/spreadsheets/d/1ABC...XYZ/edit
   ID: 1ABC...XYZ

### 7. Предоставьте доступ Service Account
1. В Google Sheets нажмите "Поделиться"
2. Вставьте email Service Account (из JSON файла, поле "client_email")
3. Выберите роль "Редактор"
4. Нажмите "Поделиться"

### 8. Обновите .env файл
Добавьте в .env:
```
GOOGLE_SHEET_ID=ваш_id_таблицы
GOOGLE_CREDENTIALS_FILE=google_credentials.json
```