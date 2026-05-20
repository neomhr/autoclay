"""SQLite output for Clay CPJ results."""

import sqlite3


UNIQUE_KEYS = {
    "companies": "domain",
    "people": "linkedin_url",
    "jobs": "url",
}


def write_sqlite(records, output_file, entity="people"):
    """Write records to an entity-specific SQLite table."""
    table = f"clay_{entity}"
    if not records:
        conn = sqlite3.connect(output_file)
        conn.close()
        return (0, 0)

    headers = records[0].field_names()
    unique_key = UNIQUE_KEYS.get(entity, headers[0])
    column_defs = []
    for header in headers:
        suffix = " UNIQUE" if header == unique_key else ""
        column_defs.append(f"{header} TEXT{suffix}")

    conn = sqlite3.connect(output_file)
    cur = conn.cursor()
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {", ".join(column_defs)},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    placeholders = ", ".join(f":{header}" for header in headers)
    columns = ", ".join(headers)
    inserted = 0
    for record in records:
        cur.execute(
            f"INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})",
            record.to_dict(),
        )
        if cur.rowcount == 1:
            inserted += 1

    conn.commit()
    conn.close()
    return (inserted, len(records) - inserted)
