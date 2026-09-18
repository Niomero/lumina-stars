from fastapi import APIRouter

from app.api.v1 import admin, auth, balance, catalog, me, orders, referrals, rent, telegram

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(catalog.router)
api_router.include_router(orders.router)
api_router.include_router(balance.router)
api_router.include_router(referrals.router)
api_router.include_router(rent.router)
api_router.include_router(admin.router)
api_router.include_router(telegram.router)
