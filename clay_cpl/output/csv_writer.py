"""CSV output for Clay CPJ results."""

import csv


def write_csv(records, output_file, entity=None):
    """Write records to a CSV file."""
    if not records:
        headers = []
    else:
        headers = records[0].field_names()

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if headers:
            writer.writeheader()
            for record in records:
                writer.writerow(record.to_dict())

    return len(records)
