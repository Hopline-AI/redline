"""Canonical condition field vocabulary — injected into generation prompts and
the inference system message to keep the model's output within a bounded set."""

CANONICAL_FIELDS: dict[str, str] = {
    "employee.location_state": "State where the employee works (e.g. 'CA')",
    "employee.classification": "exempt or non_exempt",
    "employee.employment_status": "active, terminated, resigned, laid_off",
    "employee.tenure_months": "Months of continuous employment",
    "employee.hours_worked_weekly": "Weekly hours worked",
    "employee.hours_worked_daily": "Daily hours worked",
    "employee.hours_worked_12_months": "Total hours in past 12 months",
    "employee.pay_type": "salaried or hourly",
    "employee.age": "Employee age in years",
    "employee.leave_type": "Type of leave requested",
    "employee.sdi_contributor": "Whether employee pays into CA SDI (true/false)",
    "employee.shift_hours": "Length of current work shift in hours",
    "employee.consecutive_workdays": "Consecutive days worked in current workweek",
    "employer.employee_count": "Total employees at the company",
    "employer.employee_count_within_75_miles": "Employees within 75 miles of worksite",
    "employer.location_state": "State where employer is headquartered/operating",
    "termination.type": "voluntary or involuntary",
    "termination.notice_given": "Whether employee gave advance notice (true/false)",
    "termination.notice_hours": "Hours of notice given before departure",
    "layoff.affected_employee_count": "Number of employees affected by layoff",
    "layoff.type": "mass_layoff, plant_closure, relocation",
    "layoff.timeframe_days": "Period in days over which layoffs occur",
    "leave.type": "family, medical, parental, bonding, caregiver",
    "leave.duration_weeks": "Duration of leave in weeks",
    "leave.reason": "Specific reason for leave",
    "break.type": "meal or rest",
    "break.duration_minutes": "Duration of break in minutes",
    "shift.start_time": "Shift start time",
    "shift.duration_hours": "Length of shift in hours",
}


def format_field_list() -> str:
    """Group fields by namespace and render as a bulleted list."""
    lines = []
    current_ns = None
    for field, desc in CANONICAL_FIELDS.items():
        ns = field.split(".")[0]
        if ns != current_ns:
            if current_ns is not None:
                lines.append("")
            current_ns = ns
        lines.append(f"  - {field}: {desc}")
    return "\n".join(lines)
