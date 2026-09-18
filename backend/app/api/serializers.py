from decimal import Decimal

from app.core.rbac import is_owner_telegram
from app.models import Order, Product, Transaction, User


def dec(value) -> str:
    if value is None:
        return "0.00"
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return f"{Decimal(str(value)):.2f}"


def user_public(user: User, balance=None, extra=None) -> dict:
    data = {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "photo_url": user.photo_url,
        "role": user.role,
        "is_blocked": user.is_blocked,
        "referral_code": user.referral_code,
        "mirror_id": user.mirror_id,
        "is_owner": is_owner_telegram(user.telegram_id),
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
    if balance is not None:
        data["balance"] = dec(balance)
    if extra:
        data.update(extra)
    return data


def product_public(product: Product, unit_price=None, total=None) -> dict:
    data = {
        "id": product.id,
        "slug": product.slug,
        "name": product.name,
        "description": product.description,
        "category": product.category,
        "icon": product.icon,
        "kind": product.kind,
        "min_quantity": product.min_quantity,
        "max_quantity": product.max_quantity,
        "step": product.step,
        "enabled": product.enabled,
        "popular": product.popular,
        "sort_order": product.sort_order,
    }
    if unit_price is not None:
        data["unit_price"] = dec(unit_price)
    if total is not None:
        data["preview_total"] = dec(total)
    return data


def order_public(order: Order) -> dict:
    product = order.product
    return {
        "id": order.id,
        "public_id": order.public_id,
        "product": product_public(product) if product else {"id": order.product_id},
        "quantity": order.quantity,
        "unit_price": dec(order.unit_price),
        "total_price": dec(order.total_price),
        "currency": order.currency,
        "status": order.status,
        "recipient": order.recipient,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "message": (order.payload or {}).get("message") if order.status == "APPROVED" else None,
    }


def tx_public(tx: Transaction) -> dict:
    return {
        "id": tx.id,
        "type": tx.type,
        "amount": dec(tx.amount),
        "balance_before": dec(tx.balance_before),
        "balance_after": dec(tx.balance_after),
        "status": tx.status,
        "description": tx.description,
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
    }
