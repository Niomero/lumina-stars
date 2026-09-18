from decimal import Decimal, ROUND_HALF_UP

TWOPLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value) -> Decimal:
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def percent_of(amount: Decimal, percent) -> Decimal:
    return money(money(amount) * money(percent) / Decimal("100"))


def apply_markup(provider_price: Decimal, markup_percent=0, markup_fixed=0) -> Decimal:
    base = money(provider_price)
    return money(base + percent_of(base, markup_percent) + money(markup_fixed))
