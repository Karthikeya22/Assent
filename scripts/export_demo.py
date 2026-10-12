"""Bundle a recorded run for the public /demo page (no backend needed at view time).

Pulls the case header, criteria tree and chart timeline from the running API in exactly the shapes
the Case Workspace components use, plus the recorded event log from record_fixture.
Run (API on :8000): `uv run python scripts/export_demo.py esi-002`
"""

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
API = "http://localhost:8000/api/v1"


def main(case_ref: str) -> None:
    tok = httpx.post(
        f"{API}/auth/token", json={"email": "coordinator@assent.dev", "password": "assent-dev"}
    ).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    cases = httpx.get(f"{API}/cases", params={"limit": 100}, headers=h).json()["items"]
    case = next(c for c in cases if c["patient_fhir_id"] == f"bench/{case_ref}")
    detail = httpx.get(f"{API}/cases/{case['id']}", headers=h).json()
    run_started = next(
        json.loads(line)
        for line in (ROOT / "data" / "fixtures" / f"run_{case_ref}.jsonl")
        .read_text("utf-8")
        .splitlines()
        if '"run_started"' in line
    )
    source_id = run_started["policy"].split()[0]  # the policy the recorded run used, e.g. L39240
    pols = httpx.get(f"{API}/policies", headers=h).json()
    version_id = next(p["latest_version"]["id"] for p in pols if p["source_id"] == source_id)
    pv = httpx.get(f"{API}/policy-versions/{version_id}", headers=h).json()
    timeline = httpx.get(f"{API}/cases/{case['id']}/timeline", headers=h).json()
    events = [
        json.loads(line)
        for line in (ROOT / "data" / "fixtures" / f"run_{case_ref}.jsonl")
        .read_text("utf-8")
        .splitlines()
        if line.strip()
    ]
    bundle = {
        "patient": detail["patient"],
        "service_family": detail["service_family"],
        "cpt_codes": detail["cpt_codes"],
        "icd10_codes": detail["icd10_codes"],
        "policy": {
            "sourceId": pv["policy"]["source_id"],
            "version": pv["version"],
            "title": pv["policy"]["title"],
        },
        "root": pv["criteria"],
        "chunks": timeline,
        "events": events,
    }
    out = ROOT / "apps" / "web" / "content" / "demo.json"
    out.write_text(json.dumps(bundle) + "\n", "utf-8")
    kb = out.stat().st_size // 1024
    print(f"{out.relative_to(ROOT)}: {len(events)} events, {len(timeline)} chunks, {kb} KB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "esi-002")
