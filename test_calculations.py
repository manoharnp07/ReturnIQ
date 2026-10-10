
from engine.calculations import (
    compare_recovery_options,
    allocate_returns,
    calculate_allocation_recovery
)

# 1. Compare individual recovery options
results = compare_recovery_options(
    cost_price=1400,
    new_selling_price=2500,
    refurbishment_cost=250,
    resale_percentage=0.75,
    vendor_credit_percentage=0.60,
    vendor_eligible_quantity=24,
    liquidation_percentage=0.35,
    total_quantity=40
)

print("RECOVERY OPTIONS")
for option, details in results.items():
    print(f"\n{option.upper().replace('_', ' ')}")
    for key, value in details.items():
        print(f"  {key}: {value}")


# 2. Allocate the returned products
allocation = allocate_returns(
    total_quantity=40,
    vendor_eligible_quantity=24
)

print("\nRETURN ALLOCATION")
for key, value in allocation.items():
    print(f"  {key}: {value}")


# 3. Calculate recovery for the proposed split
split_recovery = calculate_allocation_recovery(
    vendor_quantity=allocation["vendor_return_quantity"],
    refurbishment_quantity=allocation["refurbishment_quantity"],
    vendor_credit_per_unit=840,
    refurbishment_net_per_unit=1625
)

print("\nSPLIT RECOVERY")
for key, value in split_recovery.items():
    print(f"  {key}: {value}")
