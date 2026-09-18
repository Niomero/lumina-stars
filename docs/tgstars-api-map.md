# TGStars Client API map

Source: `https://tgstars.helper20sms.ru/api/swagger-internal/swagger.json`

Base URL: `https://tgstars.helper20sms.ru/api/v1/client`

Auth: `Authorization: Bearer <TGSTARS_API_KEY>`

Rate limit: 30 req/min, min 2 seconds between requests.

| Method | HTTP | Endpoint | Request | Response | Purpose |
|---|---|---|---|---|---|
| get_balance | GET | `/balance` | — | `success, user_id, username, balance_rub, balance_nano` | Provider wallet |
| get_stars_rate | GET | `/stars/rate` | — | `price_per_star_rub, price_per_star_nano, min_quantity, max_quantity, stars_enabled` | Live star price |
| check_username | GET | `/username/check` | `username, type=stars\|premium, months?` | `valid, reason` | Recipient can receive |
| create_stars_order | POST | `/orders/stars` | `{username, quantity}` | `transaction_id, quantity, total_rub, recipient` | Buy stars |
| create_premium_order | POST | `/orders/premium` | `{username, months}` | `transaction_id, months, total_rub, recipient` | Buy premium |
| get_order | GET | `/orders/{order_id}` | path id | order details | Provider order status |
| get_nft_rent_rate | GET | `/rent/nft/rate` | `nft_address, days?` | rental quote | NFT rent quote |
| create_nft_rent | POST | `/orders/rent/nft` | `{nft_address, days?}` | rental order | NFT rent (live, not used in DEMO) |
| rent_connect | POST | `/orders/rent/connect` | `{transaction_id, tonconnect_url}` | connection | TON Connect (live, not used in DEMO) |

DEMO_MODE never calls write endpoints (`/orders/*`). Reads (`/stars/rate`, `/username/check`) are used when `TGSTARS_API_KEY` is set, otherwise local fallback prices.
