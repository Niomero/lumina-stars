from typing import Any, Optional

from pydantic import BaseModel, Field


class BalanceResponse(BaseModel):
    success: bool = True
    user_id: Optional[int] = None
    username: Optional[str] = None
    balance_rub: Optional[float] = None
    balance_nano: Optional[int] = None


class StarsRateResponse(BaseModel):
    success: bool = True
    price_per_star_rub: Optional[float] = None
    price_per_star_nano: Optional[int] = None
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    stars_enabled: Optional[bool] = True


class UsernameCheckResponse(BaseModel):
    success: bool = True
    valid: Optional[bool] = None
    reason: Optional[str] = None


class StarsOrderRequest(BaseModel):
    username: str
    quantity: int = Field(ge=50, le=10000)


class StarsOrderResponse(BaseModel):
    success: bool = True
    transaction_id: Optional[int] = None
    quantity: Optional[int] = None
    total_rub: Optional[float] = None
    recipient: Optional[str] = None


class PremiumOrderRequest(BaseModel):
    username: str
    months: int


class PremiumOrderResponse(BaseModel):
    success: bool = True
    transaction_id: Optional[int] = None
    months: Optional[int] = None
    total_rub: Optional[float] = None
    recipient: Optional[str] = None


class OrderDetailsResponse(BaseModel):
    id: Optional[int] = None
    status: Optional[str] = None
    product_name: Optional[str] = None
    product_type: Optional[str] = None
    username: Optional[str] = None
    quantity: Optional[int] = None
    total_rub: Optional[float] = None
    extra: dict[str, Any] = {}
