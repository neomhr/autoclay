"""JSON output for Clay people results."""

import json


def write_json(people, output_file=None):
    """Write a list of Person objects as JSON.

    Args:
        people: List of Person instances.
        output_file: Optional path to write JSON to. If None, the JSON string
            is returned without writing to disk (useful for stdout piping).

    Returns:
        The JSON string.
    """
    payload = {
        "count": len(people),
        "people": [person.to_dict() for person in people],
    }

    json_str = json.dumps(payload, indent=2)

    if output_file is not None:
        with open(output_file, "w") as f:
            f.write(json_str)
            f.write("\n")

    return json_str
