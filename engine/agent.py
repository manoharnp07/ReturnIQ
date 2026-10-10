"""
ReturnIQ Agent Engine

Analyzes return records using explicit business rules.
This is a rule-based decision agent, not an LLM.
"""

from collections import defaultdict


def analyze_returns(records):
    """
    Analyze saved return records and produce:
    - A daily attention summary
    - At least three categories of issue detection
    - Product and batch-linked findings
    - Prioritized recommendations

    Expected record fields:
    id, product_name, sku, batch_number, quantity,
    reason, grade, cost_price, selling_price,
    vendor_eligible_quantity, status
    """

    records = [dict(record) for record in records]

    findings = []
    batch_groups = defaultdict(list)
    product_groups = defaultdict(list)

    def add_finding(
        issue_type,
        severity,
        record,
        title,
        explanation,
        recommendation,
    ):
        findings.append({
            "type": issue_type,
            "severity": severity,
            "return_id": record["id"],
            "product_name": record["product_name"],
            "sku": record["sku"],
            "batch_number": record["batch_number"],
            "title": title,
            "explanation": explanation,
            "recommendation": recommendation,
        })

    # Group records to identify repeated product and batch issues.
    for record in records:
        batch_groups[record["batch_number"]].append(record)
        product_groups[record["sku"]].append(record)

    # Problem type 1: Repeated return reasons within a batch.
    for batch_number, batch_records in batch_groups.items():
        reason_groups = defaultdict(list)

        for record in batch_records:
            reason_groups[record["reason"].strip().lower()].append(record)

        for reason, matching_records in reason_groups.items():
            total_units = sum(r["quantity"] for r in matching_records)

            if len(matching_records) >= 2:
                record = matching_records[0]

                add_finding(
                    "repeated_batch_issue",
                    "high",
                    record,
                    "Repeated return reason in batch",
                    (
                        f"Batch {batch_number} has {len(matching_records)} "
                        f"requests for the reason '{reason}', covering "
                        f"{total_units} units."
                    ),
                    (
                        "Review inspection evidence and determine whether "
                        "the batch needs a supplier-quality investigation."
                    ),
                )

    # Problem type 2: Vendor eligibility or quantity inconsistencies.
    for record in records:
        quantity = record["quantity"]
        eligible = record["vendor_eligible_quantity"]

        if quantity < 0 or eligible < 0 or eligible > quantity:
            add_finding(
                "eligibility_issue",
                "high",
                record,
                "Invalid vendor eligibility",
                (
                    f"Request #{record['id']} has {eligible} vendor-eligible "
                    f"units against {quantity} returned units."
                ),
                (
                    "Correct the quantities before approving a recovery route."
                ),
            )

    # Problem type 3: Recovery economics and condition concerns.
    for record in records:
        cost = record["cost_price"]
        selling_price = record["selling_price"]
        grade = record["grade"].strip().upper()

        refurbishment_cost = 250
        resale_percentage = 0.75

        net_refurbishment = (
            selling_price * resale_percentage - refurbishment_cost
        )

        if net_refurbishment < 0:
            add_finding(
                "poor_recovery_economics",
                "high",
                record,
                "Refurbishment may lose money",
                (
                    f"Estimated refurbishment recovery is "
                    f"₹{net_refurbishment:,.2f} per unit before "
                    "any additional logistics or handling costs."
                ),
                (
                    "Compare vendor return and liquidation before "
                    "selecting refurbishment."
                ),
            )

        if grade in {"C", "D"}:
            add_finding(
                "condition_risk",
                "medium",
                record,
                "Product condition requires review",
                (
                    f"Product {record['product_name']} has condition "
                    f"grade {grade}."
                ),
                (
                    "Verify inspection results before assuming "
                    "the units are suitable for refurbishment."
                ),
            )

    # Product-level pattern: multiple return requests for the same SKU.
    for sku, product_records in product_groups.items():
        if len(product_records) >= 3:
            record = product_records[0]
            total_units = sum(r["quantity"] for r in product_records)

            add_finding(
                "recurring_product_returns",
                "medium",
                record,
                "Repeated returns for the same product",
                (
                    f"SKU {sku} appears in {len(product_records)} return "
                    f"requests covering {total_units} units."
                ),
                (
                    "Review the return reasons and check whether a common "
                    "product or supplier issue exists."
                ),
            )

    # Prioritize high-severity findings first.
    severity_rank = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }

    findings.sort(
        key=lambda item: (
            severity_rank.get(item["severity"], 3),
            item["return_id"],
        )
    )

    high_count = sum(
        1 for item in findings if item["severity"] == "high"
    )

    medium_count = sum(
        1 for item in findings if item["severity"] == "medium"
    )

    if not records:
        summary = "No return requests are available for analysis."
    elif not findings:
        summary = (
            f"Reviewed {len(records)} return requests. "
            "No configured warning rules were triggered."
        )
    else:
        summary = (
            f"Reviewed {len(records)} return requests. "
            f"Found {len(findings)} issues: {high_count} high-priority "
            f"and {medium_count} medium-priority. "
            "Review the prioritized findings before approving actions."
        )

    return {
        "summary": summary,
        "total_records_analyzed": len(records),
        "total_findings": len(findings),
        "high_priority_count": high_count,
        "medium_priority_count": medium_count,
        "findings": findings,
    }
