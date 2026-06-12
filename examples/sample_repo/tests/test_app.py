from app import Invoice, calculate_total


def test_calculate_total_with_coupon():
    assert calculate_total(Invoice(subtotal=10_000, tax=800, coupon="WELCOME10")) == 9_800
