"""Write the OpenAPI spec without a running server: `uv run python -m assent_api.export_openapi`."""

import json
import sys

from assent_api.main import create_app

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "apps/web/lib/api/openapi.json"
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(create_app().openapi(), f, indent=2, sort_keys=True)
        f.write("\n")
