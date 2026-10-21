from datetime import datetime, timedelta

# SLA hours corresponding to priority levels
SLA_HOURS_MAP = {
    "Critical": 2,
    "High": 6,
    "Medium": 24,
    "Low": 72
}

def calculate_sla_deadline(priority="Medium", start_time=None):
    """Calculates SLA deadline datetime based on priority level."""
    if start_time is None:
        start_time = datetime.now()
    hours = SLA_HOURS_MAP.get(priority.capitalize(), 24)
    return start_time + timedelta(hours=hours)

def get_sla_status(sla_deadline, status, resolved_at=None):
    """
    Evaluates current SLA status, returning badge state and human-readable countdown text.
    """
    if not sla_deadline:
        return {"badge": "neutral", "label": "No SLA", "is_breached": False}

    if isinstance(sla_deadline, str):
        try:
            sla_deadline = datetime.fromisoformat(sla_deadline.replace("Z", ""))
        except Exception:
            sla_deadline = datetime.strptime(sla_deadline, "%Y-%m-%d %H:%M:%S")

    if isinstance(resolved_at, str):
        try:
            resolved_at = datetime.fromisoformat(resolved_at.replace("Z", ""))
        except Exception:
            resolved_at = datetime.strptime(resolved_at, "%Y-%m-%d %H:%M:%S")

    now = datetime.now()

    # If issue has been resolved or closed
    if status in ("Resolved", "Closed"):
        effective_time = resolved_at if resolved_at else now
        if effective_time <= sla_deadline:
            return {"badge": "success", "label": "Resolved Within SLA", "is_breached": False}
        else:
            diff = effective_time - sla_deadline
            hours = int(diff.total_seconds() // 3600)
            return {"badge": "danger", "label": f"Resolved (Breached by {hours}h)", "is_breached": True}

    # If still active
    if now > sla_deadline:
        overdue_diff = now - sla_deadline
        hours = int(overdue_diff.total_seconds() // 3600)
        mins = int((overdue_diff.total_seconds() % 3600) // 60)
        return {"badge": "danger", "label": f"BREACHED (+{hours}h {mins}m)", "is_breached": True}
    else:
        remaining_diff = sla_deadline - now
        hours = int(remaining_diff.total_seconds() // 3600)
        mins = int((remaining_diff.total_seconds() % 3600) // 60)
        badge = "warning" if hours < 2 else "info"
        return {"badge": badge, "label": f"{hours:02d}h {mins:02d}m remaining", "is_breached": False}
