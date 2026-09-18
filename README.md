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

Владелец и команда:

- `OWNER_TELEGRAM_ID=8565986003` — этот Telegram ID всегда SUPERADMIN
- Админов добавляет владелец в разделе «Команда» по Telegram ID или @username

Trust Pay (перевод по номеру карты, не эквайринг):

- `TRUST_PAY_CARD_NUMBER=5599002144955509`
- `YOOMONEY_WALLET=4100119621450464`
- `TRUST_PAY_CARD_HOLDER` — имя получателя (опционально)
- `TRUST_PAY_FEE_PERCENT=3`
- `TRUST_PAY_MIN_AMOUNT=30.00`

Сумма обязательна до выдачи ссылки. После ввода открывается страница оплаты с номером карты `5599 0021 4495 5509` и ЮMoney `https://yoomoney.ru/to/4100119621450464/<сумма>`. Из бота ссылки уходят как обычные URL, не как Mini App.

TGStars:

- `TGSTARS_API_URL=https://tgstars.tg/api/v1/client`
- `TGSTARS_API_KEY` — только на backend
- `DEMO_MODE=true` пока live-выдача выключена; каталог NFT / username / номеров читается живым API
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
