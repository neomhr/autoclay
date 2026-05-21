"""JSON output for Clay CPJ results."""

import json


def write_json(records, output_file=None, entity="people"):
    """Write records as JSON using the entity collection key."""
    payload = {
        "count": len(records),
        entity: [record.to_dict() for record in records],
    }

    json_str = json.dumps(payload, indent=2)

    if output_file is not None:
        with open(output_file, "w") as f:
            f.write(json_str)
            f.write("\n")

    return json_str
