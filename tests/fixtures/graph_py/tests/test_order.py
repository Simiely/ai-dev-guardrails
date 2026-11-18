from app.order import cancel


def test_cancel() -> None:
    assert cancel("o-1").startswith("cancelled")
