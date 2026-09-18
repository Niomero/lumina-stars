# TGStars Client API map

Source: `https://tgstars.helper20sms.ru/api/swagger-internal/swagger.json`

Base URL: `https://tgstars.helper20sms.ru/api/v1/client`

Auth: `Authorization: Bearer <TGSTARS_API_KEY>`

Rate limit: 30 req/min, min 2 seconds between requests.

| Method | HTTP | Endpoint | Request | Response | Purpose |
|---|---|---|---|---|---|
| get_balance | GET | `/balance` | — | `success, user_id, username, balance_rub, balance_nano` | Provider wallet |
| get_stars_rate | GET | `/stars/rate` | — | `price_per_star_rub, min_quantity, max_quantity, stars_enabled` | Live star price |
| check_username | GET | `/username/check` | `username, type=stars\|premium, months?` | `valid, reason` | Recipient can receive |
| create_stars_order | POST | `/orders/stars` | `{username, quantity}` | `transaction_id, quantity, total_rub, recipient` | Buy stars |
| create_premium_order | POST | `/orders/premium` | `{username, months}` | `transaction_id, months, total_rub, recipient` | Buy premium |
| get_order | GET | `/orders/{order_id}` | path id | order details | Provider order status |
| get_nft_rent_rate | GET | `/rent/nft/rate` | `nft_address, days?` | rental quote | NFT gift rent quote |
| get_username_rent_rate | GET | `/rent/username/rate` | `nft_address, days?` | rental quote | Username rent quote |
| get_number_rent_rate | GET | `/rent/number/rate` | `nft_address, days?` | rental quote | Number rent quote |
| rent_nft_collections | GET | `/rent/nft/collections` | — | collections | NFT rent collections |
| rent_nft_list | GET | `/rent/nft/list` | `collection_address, cursor, sort_by, model, symbol, backdrop` | items | NFT gifts for rent |
| rent_username_list | GET | `/rent/username/list` | `cursor, search, length_filter…` | items | Usernames for rent |
| rent_number_list | GET | `/rent/number/list` | `cursor, sort_by, masks…` | items | Numbers for rent |
| create_nft_rent | POST | `/orders/rent/nft` | `{nft_address, days?}` | rental order | Live NFT rent |
| create_username_rent | POST | `/orders/rent/username` | `{nft_address, days?}` | rental order | Live username rent |
| create_number_rent | POST | `/orders/rent/number` | `{nft_address, days?}` | rental order | Live number rent |
| rent_connect | POST | `/orders/rent/connect` | `{transaction_id, tonconnect_url}` | connection | TON Connect bind |
| nft_buy_collections | GET | `/nft/buy/collections` | — | collections | NFT buy collections |
| nft_buy_list | GET | `/nft/buy/list` | `collection_address, cursor, filters` | nfts | NFTs for sale |
| nft_buy_info | GET | `/nft/buy/info` | `nft_address` | nft | NFT buy details |
| buy_nft | POST | `/orders/nft/buy` | `{nft_address}` | purchase | Live NFT buy |
| transfer_nft_telegram | POST | `/orders/nft/transfer/telegram` | `{transaction_id, username}` | transfer | Send NFT to Telegram |
| transfer_nft_wallet | POST | `/orders/nft/transfer/wallet` | `{transaction_id, wallet_address}` | transfer | Send NFT to TON wallet |

DEMO_MODE never calls write endpoints (`POST /orders/*`). Catalog reads are used when `TGSTARS_API_KEY` is set; otherwise the boutique shows a local DEMO витрина with the same fields.
