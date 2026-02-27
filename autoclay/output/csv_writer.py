"""CSV output for Clay people results."""

import csv

from ..models import Person


def write_csv(people, output_file):
    """Write a list of Person objects to a CSV file.

    Args:
        people: List of Person instances.
        output_file: Path to the output CSV file.

    Returns:
        Number of rows written.
    """
    headers = Person.field_names()

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for person in people:
            writer.writerow(person.to_dict())

    return len(people)
