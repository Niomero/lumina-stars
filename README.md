# Lumina Stars

Telegram Mini App для продажи Telegram Stars. FastAPI + React + PostgreSQL.

В DEMO_MODE заказы одобряются локально, деньги списываются с внутреннего баланса, внешние write-операции TGStars не вызываются.

## Стек

- Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic
- Frontend: React 19, Vite, TanStack Query
- DB: PostgreSQL 16 (SQLite для локальных тестов)
- Deploy: Docker / Render

## Быстрый старт

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DEMO_MODE=true DEMO_LOGIN_ENABLED=true
export SECRET_KEY=dev JWT_SECRET=dev
uvicorn app.main:app --reload --port 8080
```

```bash
cd frontend
npm install
npm run build   # кладёт SPA в backend/static
```

Откройте `http://localhost:8080`. Без Telegram сработает демо-вход.

## Переменные окружения

См. `.env.example`.

Обязательные в проде:

- `DATABASE_URL`
- `SECRET_KEY` / `JWT_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBAPP_URL`

TGStars:

- `TGSTARS_API_URL=https://tgstars.helper20sms.ru/api/v1/client`
- `TGSTARS_API_KEY` — только на backend
- `DEMO_MODE=true` пока live-выдача выключена
- `TGSTARS_ENABLED=true` — чтобы RealOrderProcessor ходил в `/orders/stars` и `/orders/premium`

## Telegram

1. BotFather → ваш бот
2. `/setmenubutton` или Menu Button → Web App URL продакшен-адреса
3. Webhook: `https://<host>/api/v1/telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>`

Реферальная ссылка: `https://t.me/<bot>?start=ref_XXXXXX`

## Docker

```bash
docker compose up --build
```

## Тесты

```bash
cd backend
pytest -q
```

## Включить реальные операции

1. Положить `TGSTARS_API_KEY`
2. `DEMO_MODE=false`
3. `TGSTARS_ENABLED=true`
4. Проверить `GET /stars/rate` и баланс провайдера
5. RealOrderProcessor начнёт вызывать `POST /orders/stars` и `POST /orders/premium`
