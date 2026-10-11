
import csv
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DATA_FILES = {
    "returns": "returns.csv",
    "products": "products.csv",
    "inventory": "inventory.csv",
    "vendor_terms": "vendor_terms.csv",
    "refurbishment": "refurbishment.csv",
    "liquidation": "liquidation.csv",
    "sales": "sales.csv",
}


def load_csv(filename):
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def load_datasets():
    return {
        name: load_csv(filename)
        for name, filename in DATA_FILES.items()
    }


def validate_datasets(datasets):
    """Check dataset relationships without modifying source data."""

    products = datasets["products"]
    returns = datasets["returns"]
    inventory = datasets["inventory"]
    vendor_terms = datasets["vendor_terms"]

    product_skus = {row["sku"] for row in products}
    inventory_skus = {row["sku"] for row in inventory}
    vendor_skus = {row["sku"] for row in vendor_terms}
    return_skus = {row["sku"] for row in returns}

    return {
        "returns_without_product": sorted(return_skus - product_skus),
        "products_without_inventory": sorted(product_skus - inventory_skus),
        "products_without_vendor_terms": sorted(product_skus - vendor_skus),
        "unique_product_skus": len(product_skus),
        "unique_return_skus": len(return_skus),
    }


if __name__ == "__main__":
    datasets = load_datasets()

    print("Dataset row counts:")
    for name, rows in datasets.items():
        print(f"{name}: {len(rows)} rows")

    print("\nDataset relationship checks:")
    for name, result in validate_datasets(datasets).items():
        print(f"{name}: {result}")
