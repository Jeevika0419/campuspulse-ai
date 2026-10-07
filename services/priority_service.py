def calculate_initial_priority(severity, location="", issue_type=""):
    """
    Calculates an initial priority for a newly reported issue based on severity,
    critical campus locations, and hazard-prone issue categories.
    """
    severity = (severity or "Medium").capitalize()
    location_lower = (location or "").lower()
    type_lower = (issue_type or "").lower()

    # Base mapping
    if severity == "Critical":
        return "Critical"
    elif severity == "High":
        # Escalation condition: High severity in exam halls, data centers, or electrical hazards
        if any(k in location_lower for k in ["server", "data center", "auditorium", "exam"]) or \
           any(k in type_lower for k in ["electrical", "power", "fire", "gas"]):
            return "Critical"
        return "High"
    elif severity == "Medium":
        if any(k in type_lower for k in ["electrical", "water leak", "network"]):
            return "Medium"
        return "Medium"
    else:
        return "Low"
