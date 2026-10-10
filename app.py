import sqlite3
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    abort,
)

from engine.calculations import (
    calculate_refurbishment_recovery,
    calculate_vendor_return_recovery,
    calculate_liquidation_recovery,
    calculate_allocation_recovery,
)

from engine.agent import analyze_returns


app = Flask(__name__)

DATABASE = Path(__file__).resolve().parent / "returniq.db"

# Estimation assumptions, not live market prices.
REFURBISHMENT_COST = 250
RESALE_PERCENTAGE = 0.75
VENDOR_CREDIT_PERCENTAGE = 0.60
LIQUIDATION_PERCENTAGE = 0.35


# ---------------- DATABASE ----------------

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS returns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                sku TEXT NOT NULL,
                batch_number TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                reason TEXT NOT NULL,
                grade TEXT NOT NULL,
                cost_price REAL NOT NULL,
                selling_price REAL NOT NULL,
                vendor_eligible_quantity INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


# ---------------- DASHBOARD ----------------

@app.route("/")
def home():
    with get_db() as connection:
        stats_row = connection.execute("""
            SELECT
                COUNT(*) AS total_requests,
                COALESCE(SUM(quantity), 0) AS total_units,
                COUNT(DISTINCT sku) AS unique_products,

                COALESCE(SUM(vendor_eligible_quantity), 0)
                    AS vendor_eligible_units,

                COALESCE(SUM(
                    quantity - vendor_eligible_quantity
                ), 0) AS refurbishment_units,

                COALESCE(SUM(
                    CASE WHEN LOWER(TRIM(status)) = 'pending'
                    THEN 1 ELSE 0 END
                ), 0) AS pending_requests,

                COALESCE(SUM(
                    CASE WHEN LOWER(TRIM(status)) = 'approved'
                    THEN 1 ELSE 0 END
                ), 0) AS approved_requests,

                COALESCE(SUM(
                    CASE WHEN LOWER(TRIM(status)) = 'rejected'
                    THEN 1 ELSE 0 END
                ), 0) AS rejected_requests

            FROM returns
        """).fetchone()

        recent_returns = connection.execute("""
            SELECT *
            FROM returns
            ORDER BY id DESC
            LIMIT 5
        """).fetchall()

        all_returns = connection.execute("""
            SELECT *
            FROM returns
            ORDER BY id DESC
        """).fetchall()

        grade_counts = connection.execute("""
            SELECT grade, COUNT(*) AS request_count
            FROM returns
            GROUP BY grade
            ORDER BY grade
        """).fetchall()

        reason_counts = connection.execute("""
            SELECT reason, COUNT(*) AS request_count
            FROM returns
            GROUP BY reason
            ORDER BY request_count DESC, reason ASC
            LIMIT 5
        """).fetchall()

    # ---------------- AGENT ANALYSIS ----------------

    # Analyze actual records from the database.
    # The agent uses explicit rules, not an LLM.
    agent_analysis = analyze_returns(all_returns)

    # ---------------- RECOVERY CALCULATIONS ----------------

    vendor_recovery_total = 0.0
    refurbishment_recovery_total = 0.0
    liquidation_recovery_total = 0.0

    for record in all_returns:
        quantity = record["quantity"]
        eligible_quantity = record["vendor_eligible_quantity"]
        remaining_quantity = quantity - eligible_quantity

        vendor_result = calculate_vendor_return_recovery(
            record["cost_price"],
            VENDOR_CREDIT_PERCENTAGE,
            eligible_quantity,
        )

        refurbishment_result = calculate_refurbishment_recovery(
            record["selling_price"],
            REFURBISHMENT_COST,
            RESALE_PERCENTAGE,
        )

        liquidation_result = calculate_liquidation_recovery(
            record["cost_price"],
            LIQUIDATION_PERCENTAGE,
            quantity,
        )

        vendor_recovery_total += vendor_result["total_recovery"]

        refurbishment_recovery_total += (
            remaining_quantity
            * refurbishment_result["net_recovery"]
        )

        liquidation_recovery_total += (
            liquidation_result["total_recovery"]
        )

    stats = dict(stats_row)

    stats["estimated_vendor_recovery"] = round(
        vendor_recovery_total, 2
    )

    stats["estimated_refurbishment_recovery"] = round(
        refurbishment_recovery_total, 2
    )

    stats["estimated_total_recovery"] = round(
        vendor_recovery_total + refurbishment_recovery_total, 2
    )

    stats["estimated_liquidation_recovery"] = round(
        liquidation_recovery_total, 2
    )

    # ---------------- CHART DATA ----------------

    total_units = stats["total_units"]
    vendor_units = stats["vendor_eligible_units"]
    refurb_units = stats["refurbishment_units"]

    vendor_percent = (
        vendor_units * 100 / total_units if total_units else 0
    )

    refurb_percent = (
        refurb_units * 100 / total_units if total_units else 0
    )

    reason_counts = [dict(reason) for reason in reason_counts]

    highest_reason_count = (
        reason_counts[0]["request_count"] if reason_counts else 0
    )

    for reason in reason_counts:
        reason["percentage"] = (
            reason["request_count"] * 100 / highest_reason_count
            if highest_reason_count else 0
        )

    return render_template(
        "dashboard.html",
        stats=stats,
        recent_returns=recent_returns,
        grade_counts=grade_counts,
        reason_counts=reason_counts,
        vendor_percent=vendor_percent,
        refurb_percent=refurb_percent,
        agent_analysis=agent_analysis,
    )


# ---------------- RETURN LIST ----------------

@app.route("/returns")
def returns_list():
    with get_db() as connection:
        returns = connection.execute("""
            SELECT *
            FROM returns
            ORDER BY id DESC
        """).fetchall()

    return render_template("returns.html", returns=returns)


# ---------------- CREATE RETURN ----------------

@app.route("/returns/new", methods=["GET", "POST"])
def create_return():
    errors = []
    form = {}

    if request.method == "POST":
        form = request.form.to_dict()

        product_name = form.get("product_name", "").strip()
        sku = form.get("sku", "").strip()
        batch_number = form.get("batch_number", "").strip()
        reason = form.get("reason", "").strip()
        grade = form.get("grade", "").strip().upper()

        try:
            quantity = int(form.get("quantity", ""))
            cost_price = float(form.get("cost_price", ""))
            selling_price = float(form.get("selling_price", ""))
            eligible_quantity = int(
                form.get("vendor_eligible_quantity", "")
            )
        except (ValueError, TypeError):
            errors.append(
                "Enter valid numbers for quantity, prices "
                "and vendor eligibility."
            )
        else:
            if not product_name:
                errors.append("Product name is required.")

            if not sku:
                errors.append("SKU is required.")

            if not batch_number:
                errors.append("Batch number is required.")

            if not reason:
                errors.append("Return reason is required.")

            if grade not in {"A", "B", "C", "D"}:
                errors.append("Select a valid condition grade.")

            if quantity <= 0:
                errors.append("Quantity must be greater than zero.")

            if cost_price <= 0:
                errors.append("Unit cost must be greater than zero.")

            if selling_price <= 0:
                errors.append("Selling price must be greater than zero.")

            if not 0 <= eligible_quantity <= quantity:
                errors.append(
                    "Vendor-eligible quantity must be between "
                    "zero and the total quantity."
                )

        if not errors:
            with get_db() as connection:
                connection.execute("""
                    INSERT INTO returns (
                        product_name,
                        sku,
                        batch_number,
                        quantity,
                        reason,
                        grade,
                        cost_price,
                        selling_price,
                        vendor_eligible_quantity
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    product_name,
                    sku,
                    batch_number,
                    quantity,
                    reason,
                    grade,
                    cost_price,
                    selling_price,
                    eligible_quantity,
                ))

            return redirect(url_for("returns_list"))

    return render_template(
        "new_return.html",
        errors=errors,
        form=form,
    )


# ---------------- REVIEW ACTIONS ----------------

@app.route("/returns/<int:return_id>/review", methods=["POST"])
def review_return(return_id):
    action = request.form.get("action", "").strip().lower()

    if action not in {"approve", "reject"}:
        abort(400, description="Invalid review action.")

    new_status = "Approved" if action == "approve" else "Rejected"

    with get_db() as connection:
        record = connection.execute("""
            SELECT id, status
            FROM returns
            WHERE id = ?
        """, (return_id,)).fetchone()

        if record is None:
            abort(404, description="Return request not found.")

        if record["status"].strip().lower() != "pending":
            abort(
                409,
                description="This request has already been reviewed."
            )

        connection.execute("""
            UPDATE returns
            SET status = ?
            WHERE id = ?
        """, (new_status, return_id))

    return redirect(url_for("return_detail", return_id=return_id))


# ---------------- RETURN DETAILS ----------------

def build_return_detail(record):
    total_quantity = record["quantity"]
    vendor_eligible_quantity = record["vendor_eligible_quantity"]

    cost_price = record["cost_price"]
    new_selling_price = record["selling_price"]

    refurbishment = calculate_refurbishment_recovery(
        new_selling_price,
        REFURBISHMENT_COST,
        RESALE_PERCENTAGE,
    )

    vendor_return = calculate_vendor_return_recovery(
        cost_price,
        VENDOR_CREDIT_PERCENTAGE,
        vendor_eligible_quantity,
    )

    liquidation = calculate_liquidation_recovery(
        cost_price,
        LIQUIDATION_PERCENTAGE,
        total_quantity,
    )

    refurbishment_quantity = (
        total_quantity - vendor_eligible_quantity
    )

    allocation_recovery = calculate_allocation_recovery(
        vendor_quantity=vendor_eligible_quantity,
        refurbishment_quantity=refurbishment_quantity,
        vendor_credit_per_unit=vendor_return["credit_per_unit"],
        refurbishment_net_per_unit=refurbishment["net_recovery"],
    )

    return {
        "record": record,
        "return_id": record["id"],
        "status": record["status"],
        "total_quantity": total_quantity,
        "vendor_eligible_quantity": vendor_eligible_quantity,
        "refurbishment_quantity": refurbishment_quantity,
        "cost_price": cost_price,
        "new_selling_price": new_selling_price,
        "refurbishment": refurbishment,
        "vendor_return": vendor_return,
        "liquidation": liquidation,
        "allocation_recovery": allocation_recovery,
    }


@app.route("/returns/hb-09")
def sample_return_detail():
    with get_db() as connection:
        record = connection.execute("""
            SELECT *
            FROM returns
            WHERE sku = 'HB-09' OR batch_number = 'HB-09'
            ORDER BY id ASC
            LIMIT 1
        """).fetchone()

    if record is None:
        abort(404, description="No HB-09 return record exists.")

    return render_template(
        "return_detail.html",
        **build_return_detail(record),
    )


@app.route("/returns/<int:return_id>")
def return_detail(return_id):
    with get_db() as connection:
        record = connection.execute("""
            SELECT *
            FROM returns
            WHERE id = ?
        """, (return_id,)).fetchone()

    if record is None:
        abort(404, description="Return request not found.")

    detail_data = build_return_detail(record)

    return render_template(
        "return_detail.html",
        **detail_data,
    )


# ---------------- APPLICATION START ----------------

init_db()


if __name__ == "__main__":
    app.run(debug=True)
