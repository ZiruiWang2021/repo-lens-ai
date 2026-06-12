from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Invoice:
    subtotal: int
    tax: int
    coupon: str | None = None


def calculate_total(invoice: Invoice) -> int:
    """Return the final amount in cents."""
    total = invoice.subtotal + invoice.tax
    if invoice.coupon == "WELCOME10":
        total -= min(1000, total // 10)
    return max(total, 0)


def render_receipt(invoice: Invoice) -> str:
    total = calculate_total(invoice)
    return f"Total due: {total} cents"
