import re
from core.database import get_all_records

# ── Constants ────────────────────────────────────────────────────

VALID_SHIFTS = {"morning", "afternoon", "night", "a", "b", "c", "1", "2", "3", "i", "ii", "iii"}

# Normalize shift display names
SHIFT_DISPLAY_MAP = {
    "i": "I", "ii": "II", "iii": "III",
    "a": "A", "b": "B", "c": "C",
    "1": "1", "2": "2", "3": "3",
    "morning": "Morning", "afternoon": "Afternoon", "night": "Night",
}

MACHINE_NUMBER_PATTERN = re.compile(r"^[A-Z0-9\-]{2,15}$", re.IGNORECASE)
OPERATION_CODE_PATTERN = re.compile(r"^[A-Z0-9\-]{2,15}$", re.IGNORECASE)
WORK_ORDER_PATTERN = re.compile(r"^[A-Z0-9\-]{3,20}$", re.IGNORECASE)

MAX_QUANTITY = 10_000   # suspicious if above this
MAX_TIME_HOURS = 24     # a single shift can't exceed 24 hours

# ── Main validator ───────────────────────────────────────────────

def validate_record(data: dict, existing_records: list = None) -> list:
    """
    Runs all business rules on an extracted/edited record.
    Returns a list of error/warning strings (empty = all good).
    """
    errors = []

    # 1. Mandatory field checks
    mandatory = ["date", "shift", "employee_number", "machine_number", "work_order_number"]
    for field in mandatory:
        if not data.get(field):
            errors.append(f"Missing mandatory field: {field.replace('_', ' ').title()}")

    # 2. Shift value check
    shift = data.get("shift")
    if shift and shift.strip().lower() not in VALID_SHIFTS:
        errors.append(f"Invalid shift value: '{shift}'. Expected Morning/Afternoon/Night or A/B/C.")

    # 3. Machine number format
    machine = data.get("machine_number")
    if machine and not MACHINE_NUMBER_PATTERN.match(machine.strip()):
        errors.append(f"Machine number '{machine}' has unexpected format (expected alphanumeric, 2-15 chars).")

    # 4. Operation code format
    op_code = data.get("operation_code")
    if op_code and not OPERATION_CODE_PATTERN.match(op_code.strip()):
        errors.append(f"Operation code '{op_code}' has unexpected format.")

    # 5. Work order format
    wo = data.get("work_order_number")
    if wo and not WORK_ORDER_PATTERN.match(wo.strip()):
        errors.append(f"Work order number '{wo}' has unexpected format.")

    # 6. Quantity checks
    qty = data.get("quantity_produced")
    if qty is None:
        errors.append("Quantity produced is missing.")
    else:
        try:
            qty_f = float(qty)
            if qty_f < 0:
                errors.append("Quantity produced cannot be negative.")
            elif qty_f == 0:
                errors.append("Quantity produced is zero — please verify.")
            elif qty_f > MAX_QUANTITY:
                errors.append(f"Quantity produced ({qty_f}) is suspiciously high (>{MAX_QUANTITY}). Please verify.")
        except (ValueError, TypeError):
            errors.append(f"Quantity produced '{qty}' is not a valid number.")

    # 7. Time taken checks
    time_val = data.get("time_taken")
    if time_val is not None:
        try:
            t = float(time_val)
            if t <= 0:
                errors.append("Time taken must be a positive number.")
            elif t > MAX_TIME_HOURS:
                errors.append(f"Time taken ({t}) exceeds 24 hours — please verify units.")
        except (ValueError, TypeError):
            errors.append(f"Time taken '{time_val}' is not a valid number.")

    # 8. Duplicate work order check
    if wo:
        records = existing_records if existing_records is not None else get_all_records()
        current_id = data.get("id")  # None for new records
        duplicates = [
            r for r in records
            if r.get("work_order_number") == wo and r.get("id") != current_id
        ]
        if duplicates:
            errors.append(f"Duplicate work order number '{wo}' found in {len(duplicates)} existing record(s).")

    return errors

# ── Confidence helpers ───────────────────────────────────────────

def get_confidence_color(score: float) -> str:
    """Returns a color string based on confidence score for UI display."""
    if score >= 0.85:
        return "green"
    elif score >= 0.60:
        return "orange"
    else:
        return "red"

def get_confidence_label(score: float) -> str:
    if score >= 0.85:
        return "High"
    elif score >= 0.60:
        return "Medium"
    else:
        return "Low"

def fields_needing_review(confidence_scores: dict, threshold: float = 0.70) -> list:
    """Returns list of field names with confidence below threshold."""
    return [
        field for field, score in confidence_scores.items()
        if score < threshold
    ]
