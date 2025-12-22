# Настройка GigaChat API для LogStorm

## 🚀 Быстрый старт

### 1. Получение API ключа

1. Перейдите на https://developers.sber.ru/studio/workspaces
2. Войдите через Сбер ID
3. Создайте проект и выберите его
4. **ВАЖНО**: Скопируйте **Authorization data** (НЕ Client Secret!)
   - Authorization data - это уже готовая base64 строка
   - Она находится в разделе с учетными данными проекта

### 2. Установка библиотеки

```bash
pip install gigachat python-dotenv
```

### 3. Настройка API ключа

⚠️ **КРИТИЧНО**: GigaChat требует **Authorization data** в формате base64!

#### Способ 1: Authorization data (РЕКОМЕНДУЕТСЯ)

1. Скопируйте `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```

2. Откройте `.env` и вставьте ваш Authorization data:
   ```env
   GIGACHAT_API_KEY=ваш_authorization_data_здесь
   GIGACHAT_SCOPE=GIGACHAT_API_PERS
   ```

#### Способ 2: Кодирование Client ID и Secret

Если у вас только Client ID и Client Secret:

1. Запустите вспомогательный скрипт:
   ```bash
   python encode_credentials.py
   ```

2. Следуйте инструкциям и скопируйте результат в `.env`

### 4. Проверка настройки

```bash
python setup.py
```

Скрипт проверит наличие API ключа и других зависимостей.

## 📋 Что делает AI анализ?

GigaChat анализирует данные посещаемости и генерирует:
- ✅ Общую оценку дисциплины команды
- ⚠️ Выявление ключевых проблем
- 🎯 Позитивные моменты
- 💡 Рекомендации для руководства

## 📁 Результаты

После запуска создается файл `ai_summary.txt` с AI-анализом.

## ❓ Частые проблемы

### "Invalid credentials format"
**Причина**: Используется Client Secret вместо Authorization data.

**Решение**: 
1. Запустите `python encode_credentials.py` 
2. Или получите Authorization data из личного кабинета

### "Authorization error: header is incorrect"
**Причина**: Неверный формат ключа (401 ошибка).

**Решение**: Убедитесь, что GIGACHAT_API_KEY содержит base64 строку:
- Либо Authorization data из личного кабинета
- Либо результат кодирования `ClientID:ClientSecret` в base64

### "GigaChat не установлен"
```bash
pip install gigachat python-dotenv
```

### "Не найден API ключ GigaChat"
Проверьте наличие `.env` файла и правильность ключа:
```bash
python setup.py
```

## 🔒 Безопасность

⚠️ **Никогда не публикуйте свой API ключ в коде или репозитории!**

Используйте переменные окружения или файлы конфигурации (добавьте в `.gitignore`).

## 📚 Документация

Полная документация GigaChat API:
https://developers.sber.ru/docs/ru/gigachat/api/overview
