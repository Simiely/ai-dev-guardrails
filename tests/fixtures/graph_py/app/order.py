from app.payment import charge


def cancel(order_id: str) -> str:
    charge(1)
    return f"cancelled:{order_id}"
