# NotiMate Sales Bot

LINE OA бот-менеджер по продажам для NotiMate.
Отвечает только в личных сообщениях. Ведёт диалог на тайском.

## Deploy на Railway

1. Fork репо
2. New Project → Deploy from GitHub
3. Добавить Variables (см. .env.example)
4. Скопировать URL → вставить в LINE Developers → Webhook URL

## Webhook URL

`https://your-app.up.railway.app/webhook`

## Стек

Flask + LINE SDK v3 + Claude Haiku + Railway
