# NotiMate Sales Bot

AI-бот-менеджер по продажам для LINE OA (часть продукта NotiMate).
Общается с потенциальными клиентами в личных сообщениях, ведёт диалог
на трёх языках (русский / английский / тайский), собирает данные
о запросе и передаёт готовый лид владельцу бизнеса.

## Стек
- Python / Flask
- Claude API (Haiku) — диалог, квалификация лида, мультиязычность
- LINE Messaging API (SDK v3, webhook)
- Deploy: Railway

## Как работает
1. Посетитель пишет боту в LINE
2. Claude ведёт диалог по системному промпту: роль менеджера,
   ограничения, цель — собрать контакты и суть запроса
3. Автоопределение языка клиента (ru / en / th)
4. Готовый лид уходит владельцу в LINE

## Статус
Работал в продакшене (Таиланд, 2025–2026) как часть NotiMate.

## Деплой на Railway
1. Fork репо
2. New Project → Deploy from GitHub
3. Добавить Variables (см. `.env.example`)
4. Скопировать URL приложения → LINE Developers → Webhook URL:
   `https://your-app.up.railway.app/webhook`

## Локальный запуск
1. `cp .env.example .env` — заполнить ключи
2. `pip install -r requirements.txt`
3. `python app.py`