
from datetime import date, datetime


def parse_date(value):
    """Convert an ISO date string to a date object."""
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def calculate_vendor_recovery(return_record, product, vendor_terms, as_of_date):
    """Calculate vendor credit when supplier terms allow a return."""

    if vendor_terms["rtv_allowed"].strip().lower() != "yes":
        return {
            "eligible": False,
            "reason": "Supplier does not allow vendor returns.",
            "net_recovery": 0.0,
        }

    received = parse_date(return_record["date_received"])
    today = parse_date(as_of_date)
    window_days = int(vendor_terms["window_days"])
    elapsed_days = (today - received).days

    if elapsed_days < 0:
        return {
            "eligible": False,
            "reason": "Return date is in the future.",
            "net_recovery": 0.0,
        }

    if elapsed_days > window_days:
        return {
            "eligible": False,
            "reason": "Vendor return window has expired.",
            "net_recovery": 0.0,
        }

    credit_pct = float(vendor_terms["credit_pct"])
    cost_price = float(product["cost_price"])

    return {
        "eligible": True,
        "reason": f"Within the {window_days}-day vendor window.",
        "net_recovery": round(cost_price * credit_pct, 2),
    }


def calculate_refurbishment_recovery(product, refurbishment_rule):
    """Estimate per-unit resale proceeds less refurbishment cost."""

    selling_price = float(product["selling_price"])
    resale_pct = float(refurbishment_rule["resale_pct_of_new"])
    refurb_cost = float(refurbishment_rule["refurb_cost"])

    resale_value = selling_price * resale_pct
    net_recovery = resale_value - refurb_cost

    return {
        "resale_value": round(resale_value, 2),
        "refurbishment_cost": round(refurb_cost, 2),
        "net_recovery": round(net_recovery, 2),
        "days_required": int(refurbishment_rule["days_required"]),
    }


def calculate_liquidation_recovery(product, condition_grade, liquidation_rule):
    """Estimate liquidation proceeds per unit."""

    cost_price = float(product["cost_price"])
    recovery_pct = float(liquidation_rule["recovery_pct_of_cost"])

    return {
        "recovery_percentage": recovery_pct,
        "net_recovery": round(cost_price * recovery_pct, 2),
        "condition_grade": condition_grade,
    }


def recommend_recovery(options):
    """Choose the highest positive eligible per-unit recovery."""

    eligible_options = [
        (name, result["net_recovery"])
        for name, result in options.items()
        if result.get("eligible", True) and result["net_recovery"] > 0
    ]

    if not eligible_options:
        return {
            "recommendation": "REVIEW",
            "reason": "No positive eligible recovery option was found.",
        }

    name, amount = max(eligible_options, key=lambda item: item[1])

    return {
        "recommendation": name.upper(),
        "estimated_recovery_per_unit": round(amount, 2),
        "reason": "Highest positive eligible estimated recovery per unit.",
    }
