"""SQLite output for Clay people results."""

import sqlite3


def write_sqlite(people, output_file):
    """Write a list of Person objects to a SQLite database.

    Creates (or reuses) a `clay_people` table with a UNIQUE constraint on
    linkedin_url.  Duplicate linkedin_urls are silently skipped via
    INSERT OR IGNORE.

    Args:
        people: List of Person instances.
        output_file: Path to the SQLite database file.

    Returns:
        Tuple of (inserted_count, skipped_count).
    """
    conn = sqlite3.connect(output_file)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS clay_people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT,
            last_name TEXT,
            full_name TEXT,
            job_title TEXT,
            location TEXT,
            company_domain TEXT,
            linkedin_url TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    inserted = 0
    for person in people:
        d = person.to_dict()
        cur.execute(
            """INSERT OR IGNORE INTO clay_people
               (first_name, last_name, full_name, job_title, location, company_domain, linkedin_url)
               VALUES (:first_name, :last_name, :full_name, :job_title, :location, :company_domain, :linkedin_url)""",
            d,
        )
        if cur.rowcount == 1:
            inserted += 1

    conn.commit()
    conn.close()

    skipped = len(people) - inserted
    return (inserted, skipped)
