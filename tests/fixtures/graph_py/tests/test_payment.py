from app.payment import charge


def test_charge() -> None:
    assert charge(1) == 1
