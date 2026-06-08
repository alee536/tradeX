from decimal import Decimal, InvalidOperation, ROUND_DOWN

COIN_QUANT = Decimal('0.00000001')


def to_decimal(value):
    """Normalize monetary/coin values to 8 decimal places."""
    if value is None or value == '':
        return Decimal('0')
    if isinstance(value, Decimal):
        return value.quantize(COIN_QUANT, rounding=ROUND_DOWN)
    try:
        return Decimal(str(value)).quantize(COIN_QUANT, rounding=ROUND_DOWN)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0')


def exceeds_balance(amount, available):
    """Return True when amount is strictly greater than available balance."""
    return to_decimal(amount) > to_decimal(available)
