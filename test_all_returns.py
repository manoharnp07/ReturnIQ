
from collections import Counter

from engine.dataset_loader import load_datasets
from engine.recovery_engine import (
    calculate_vendor_recovery,
    calculate_refurbishment_recovery,
    calculate_liquidation_recovery,
    recommend_recovery,
)

SNAPSHOT_DATE = "2026-11-16"


def main():
    data = load_datasets()

    products = {row["sku"]: row for row in data["products"]}
    terms = {row["sku"]: row for row in data["vendor_terms"]}
    refurbishment = {
        row["category"]: row for row in data["refurbishment"]
    }
    liquidation = {
        (row["category"], row["condition_grade"]): row
        for row in data["liquidation"]
    }

    recommendations = Counter()
    errors = []
    tested = 0

    for returned in data["returns"]:
        try:
            sku = returned["sku"]
            product = products[sku]

            vendor = calculate_vendor_recovery(
                returned, product, terms[sku], SNAPSHOT_DATE
            )

            refurb_rule = refurbishment[product["category"]]
            refurb = calculate_refurbishment_recovery(
                product, refurb_rule
            )

            key = (product["category"], returned["condition_grade"])
            liquidation_rule = liquidation[key]
            liquid = calculate_liquidation_recovery(
                product, returned["condition_grade"], liquidation_rule
            )

            result = recommend_recovery({
                "vendor_return": vendor,
                "refurbishment": refurb,
                "liquidation": liquid,
            })

            recommendations[result["recommendation"]] += 1
            tested += 1

        except (KeyError, ValueError, TypeError) as exc:
            errors.append({
                "return_id": returned.get("return_id"),
                "sku": returned.get("sku"),
                "error": str(exc),
            })

    print(f"Total returns: {len(data['returns'])}")
    print(f"Successfully tested: {tested}")
    print(f"Errors: {len(errors)}")
    print(f"Recommendations: {dict(recommendations)}")

    if errors:
        print("\nFirst 10 errors:")
        for error in errors[:10]:
            print(error)


if __name__ == "__main__":
    main()
