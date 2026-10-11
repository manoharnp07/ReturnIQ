
from engine.dataset_loader import load_datasets
from engine.recovery_engine import (
    calculate_vendor_recovery,
    calculate_refurbishment_recovery,
    calculate_liquidation_recovery,
    recommend_recovery,
)

SNAPSHOT_DATE = "2026-11-16"


def find_by(rows, **criteria):
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            return row
    raise ValueError(f"No matching row found: {criteria}")


def main():
    data = load_datasets()

    # Select an actual return and match its product.
    returned = data["returns"][0]
    product = find_by(data["products"], sku=returned["sku"])
    terms = find_by(
        data["vendor_terms"],
        sku=returned["sku"],
    )

    refurbishment_rule = find_by(
        data["refurbishment"],
        category=product["category"],
    )

    liquidation_rule = find_by(
        data["liquidation"],
        category=product["category"],
        condition_grade=returned["condition_grade"],
    )

    vendor = calculate_vendor_recovery(
        returned, product, terms, SNAPSHOT_DATE
    )
    refurbishment = calculate_refurbishment_recovery(
        product, refurbishment_rule
    )
    liquidation = calculate_liquidation_recovery(
        product, returned["condition_grade"], liquidation_rule
    )

    options = {
        "vendor_return": vendor,
        "refurbishment": refurbishment,
        "liquidation": liquidation,
    }

    print("RETURN:", returned["return_id"])
    print("SKU:", returned["sku"])
    print("PRODUCT:", product["product"])
    print("CONDITION:", returned["condition_grade"])
    print("\nRECOVERY OPTIONS")
    for name, result in options.items():
        print(f"{name}: {result}")

    print("\nRECOMMENDATION")
    print(recommend_recovery(options))


if __name__ == "__main__":
    main()
