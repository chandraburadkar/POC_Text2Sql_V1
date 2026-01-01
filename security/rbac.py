PERSONA_TABLE_ACCESS = {
    "executive": {"flight_ops_daily"},
    "ops_manager": {"flight_ops_daily", "incident_log"},
    "analyst": {"*"},
}

def check_table_access(persona: str, tables: list[str]) -> bool:
    allowed = PERSONA_TABLE_ACCESS.get(persona, set())
    if "*" in allowed:
        return True
    return all(t in allowed for t in tables)
