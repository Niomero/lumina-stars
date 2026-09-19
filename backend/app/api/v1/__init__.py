from fastapi import APIRouter

from app.api.v1 import admin, admin_ext, auth, balance, catalog, digital, giveaways, me, orders, promos, public, referrals, rent, telegram, trust_pay

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(catalog.router)
api_router.include_router(orders.router)
api_router.include_router(balance.router)
api_router.include_router(referrals.router)
api_router.include_router(rent.router)
api_router.include_router(trust_pay.router)
api_router.include_router(digital.router)
api_router.include_router(giveaways.router)
api_router.include_router(admin.router)
api_router.include_router(admin_ext.router)
api_router.include_router(telegram.router)
api_router.include_router(public.router)
api_router.include_router(promos.router)
