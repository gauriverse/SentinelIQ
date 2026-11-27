"""Generate deterministic simulated activity, save it, and optionally load it via the API.

    python -m simulator.cli --days 45 --seed 42 --load
"""
import argparse
import getpass
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

from simulator.dataset import build_dataset
from simulator.generators.employees import build_profile

CHUNK = 1000  # the API accepts at most 1000 events per bulk request


class Api:
    def __init__(self, url: str, org: str, username: str, password: str) -> None:
        self.http = httpx.Client(base_url=url, timeout=60)
        self.creds = {"organization": org, "username": username, "password": password}
        self.login()

    def login(self) -> None:
        res = self.http.post("/api/v1/auth/login", json=self.creds)
        res.raise_for_status()
        self.http.headers["Authorization"] = f"Bearer {res.json()['access_token']}"

    def request(self, method: str, path: str, **kw) -> httpx.Response:
        res = self.http.request(method, path, **kw)
        if res.status_code == 401:  # token expired during a long load
            self.login()
            res = self.http.request(method, path, **kw)
        res.raise_for_status()
        return res

    def employees(self) -> list[dict]:
        items, offset = [], 0
        while True:
            page = self.request("GET", "/api/v1/users", params={"limit": 200, "offset": offset}).json()
            items += page["items"]
            offset += 200
            if offset >= page["total"]:
                return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--org", default="Acme Corp")
    ap.add_argument("--username", default="admin")
    ap.add_argument("--days", type=int, default=45)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--start", help="YYYY-MM-DD; default is today minus --days")
    ap.add_argument("--out", default="data/sim")
    ap.add_argument("--load", action="store_true", help="POST events to the API")
    args = ap.parse_args()

    today = datetime.now(timezone.utc).date()
    start = date.fromisoformat(args.start) if args.start else today - timedelta(days=args.days)
    if start + timedelta(days=args.days) > today:
        raise SystemExit("The simulated period must end today or earlier (no future events).")

    password = os.getenv("SIM_PASSWORD") or getpass.getpass("Admin password: ")
    api = Api(args.url, args.org, args.username, password)

    employees = api.employees()
    if not employees:
        raise SystemExit("No employees found. Run: python -m app.scripts.seed_employees")
    profiles = [build_profile(e["id"], e["department"] or "Support", args.seed) for e in employees]

    events, labels = build_dataset(profiles, start, args.days, args.seed)
    print(f"{len(employees)} employees, {len(events):,} events, {len(labels)} labelled attack events")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "events.jsonl").open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    (out / "labels.json").write_text(json.dumps(labels, indent=1), encoding="utf-8")
    print(f"Saved to {out}/events.jsonl and labels.json")

    if args.load:
        inserted = duplicates = 0
        for i in range(0, len(events), CHUNK):
            res = api.request("POST", "/api/v1/events/bulk", json={"events": events[i:i + CHUNK]}).json()
            inserted += res["inserted"]
            duplicates += res["duplicates"]
            if (i // CHUNK) % 10 == 0:
                print(f"  {i + CHUNK:,}/{len(events):,}")
        print(f"Loaded: {inserted:,} inserted, {duplicates:,} duplicates")


if __name__ == "__main__":
    main()