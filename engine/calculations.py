def calculate_refurbishment_recovery(
    new_selling_price,
    refurbishment_cost,
    resale_percentage
):
    refurbished_selling_price = round(
        new_selling_price * resale_percentage, 2
    )

    net_recovery = round(
        refurbished_selling_price - refurbishment_cost, 2
    )

    return {
        "refurbished_selling_price": refurbished_selling_price,
        "refurbishment_cost": refurbishment_cost,
        "net_recovery": net_recovery
    }


def calculate_vendor_return_recovery(
    cost_price,
    credit_percentage,
    eligible_quantity
):
    credit_per_unit = round(
        cost_price * credit_percentage, 2
    )

    total_recovery = round(
        credit_per_unit * eligible_quantity, 2
    )

    return {
        "eligible_quantity": eligible_quantity,
        "credit_per_unit": credit_per_unit,
        "total_recovery": total_recovery
    }


def calculate_liquidation_recovery(
    cost_price,
    recovery_percentage,
    quantity
):
    recovery_per_unit = round(
        cost_price * recovery_percentage, 2
    )

    total_recovery = round(
        recovery_per_unit * quantity, 2
    )

    return {
        "quantity": quantity,
        "recovery_per_unit": recovery_per_unit,
        "total_recovery": total_recovery
    }


def compare_recovery_options(
    cost_price,
    new_selling_price,
    refurbishment_cost,
    resale_percentage,
    vendor_credit_percentage,
    vendor_eligible_quantity,
    liquidation_percentage,
    total_quantity
):
    refurbishment = calculate_refurbishment_recovery(
        new_selling_price,
        refurbishment_cost,
        resale_percentage
    )

    vendor_return = calculate_vendor_return_recovery(
        cost_price,
        vendor_credit_percentage,
        vendor_eligible_quantity
    )

    liquidation = calculate_liquidation_recovery(
        cost_price,
        liquidation_percentage,
        total_quantity
    )

    return {
        "refurbishment": {
            "quantity": total_quantity,
            "recovery_per_unit": refurbishment["net_recovery"],
            "total_recovery": round(
                refurbishment["net_recovery"] * total_quantity, 2
            )
        },
        "vendor_return": vendor_return,
        "liquidation": liquidation
    }


def allocate_returns(
    total_quantity,
    vendor_eligible_quantity
):
    if total_quantity < 0:
        raise ValueError("Total quantity cannot be negative.")

    if not 0 <= vendor_eligible_quantity <= total_quantity:
        raise ValueError(
            "Vendor-eligible quantity must be between 0 and total quantity."
        )

    vendor_quantity = vendor_eligible_quantity
    refurbishment_quantity = total_quantity - vendor_quantity

    return {
        "total_quantity": total_quantity,
        "vendor_return_quantity": vendor_quantity,
        "refurbishment_quantity": refurbishment_quantity,
        "unallocated_quantity": 0
    }


def calculate_allocation_recovery(
    vendor_quantity,
    refurbishment_quantity,
    vendor_credit_per_unit,
    refurbishment_net_per_unit
):
    vendor_recovery = round(
        vendor_quantity * vendor_credit_per_unit, 2
    )

    refurbishment_recovery = round(
        refurbishment_quantity * refurbishment_net_per_unit, 2
    )

    total_recovery = round(
        vendor_recovery + refurbishment_recovery, 2
    )

    return {
        "vendor_recovery": vendor_recovery,
        "refurbishment_recovery": refurbishment_recovery,
        "total_recovery": total_recovery
    }


def recommend_return_allocation(
    total_quantity,
    vendor_eligible_quantity,
    vendor_credit_per_unit,
    refurbishment_net_per_unit,
    liquidation_recovery_per_unit,
    demand_supported_quantity,
    vendor_deadline_days_remaining
):
    """
    Recommend a return allocation using explicit business rules.

    This is a rule-based recommendation, not an AI prediction.
    """

    if total_quantity < 0:
        raise ValueError("Total quantity cannot be negative.")

    if not 0 <= vendor_eligible_quantity <= total_quantity:
        raise ValueError(
            "Vendor-eligible quantity must be between 0 and total quantity."
        )

    if not 0 <= demand_supported_quantity <= total_quantity:
        raise ValueError(
            "Demand-supported quantity must be between 0 and total quantity."
        )

    if vendor_deadline_days_remaining < 0:
        raise ValueError("Deadline days cannot be negative.")

    if any(
        value < 0
        for value in (
            vendor_credit_per_unit,
            refurbishment_net_per_unit,
            liquidation_recovery_per_unit
        )
    ):
        raise ValueError("Recovery values cannot be negative.")

    # Route eligible units to the vendor if the window is open.
    if vendor_deadline_days_remaining > 0:
        vendor_quantity = vendor_eligible_quantity
    else:
        vendor_quantity = 0

    remaining_quantity = total_quantity - vendor_quantity

    # Refurbish only the remaining units supported by demand.
    refurbishment_quantity = min(
        remaining_quantity,
        demand_supported_quantity
    )

    # Route anything left to liquidation.
    liquidation_quantity = (
        remaining_quantity - refurbishment_quantity
    )

    vendor_recovery = round(
        vendor_quantity * vendor_credit_per_unit, 2
    )

    refurbishment_recovery = round(
        refurbishment_quantity * refurbishment_net_per_unit, 2
    )

    liquidation_recovery = round(
        liquidation_quantity * liquidation_recovery_per_unit, 2
    )

    total_recovery = round(
        vendor_recovery
        + refurbishment_recovery
        + liquidation_recovery,
        2
    )

    reasons = []

    if vendor_quantity > 0:
        reasons.append(
            f"Return {vendor_quantity} eligible units to the vendor "
            "while the supplier window remains open."
        )
    elif vendor_eligible_quantity > 0:
        reasons.append(
            "The vendor return window has expired; eligible units "
            "cannot be assigned to the vendor under this rule."
        )

    if refurbishment_quantity > 0:
        reasons.append(
            f"Refurbish {refurbishment_quantity} units supported by demand."
        )

    if liquidation_quantity > 0:
        reasons.append(
            f"Liquidate {liquidation_quantity} remaining units "
            "to avoid assuming unsupported resale demand."
        )

    if not reasons:
        reasons.append("No units are available for allocation.")

    return {
        "allocation": {
            "vendor_return_quantity": vendor_quantity,
            "refurbishment_quantity": refurbishment_quantity,
            "liquidation_quantity": liquidation_quantity
        },
        "recovery": {
            "vendor": vendor_recovery,
            "refurbishment": refurbishment_recovery,
            "liquidation": liquidation_recovery,
            "total": total_recovery
        },
        "recommendation_reasons": reasons,
        "assumptions": [
            "Recovery estimates exclude unprovided handling and shipping costs.",
            "Demand-supported quantity must come from user input or inventory data.",
            "A positive deadline means the vendor return window is still open."
        ]
    }
