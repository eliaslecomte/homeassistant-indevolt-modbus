"""Set repository metadata before publishing the HACS folder."""

import argparse
import json
import re
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("owner")
parser.add_argument("repository")
args = parser.parse_args()
if not all(
    re.fullmatch(r"[A-Za-z0-9_.-]+", value) for value in (args.owner, args.repository)
):
    parser.error("Use GitHub owner and repository names, not URLs")
root = Path(__file__).resolve().parents[1]
manifest = root / "custom_components/indevolt_modbus/manifest.json"
data = json.loads(manifest.read_text())
url = f"https://github.com/{args.owner}/{args.repository}"
data.update(
    codeowners=[f"@{args.owner}"], documentation=url, issue_tracker=f"{url}/issues"
)
data = {
    key: data[key]
    for key in ["domain", "name", *sorted(set(data) - {"domain", "name"})]
}
manifest.write_text(json.dumps(data, indent=2) + "\n")
