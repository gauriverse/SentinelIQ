from datetime import date, timedelta
from ipaddress import ip_address

import pytest

from simulator.dataset import DORMANT_AFTER_DAYS, build_dataset
from simulator.generators.common import iso
from simulator.generators.employees import DEPARTMENTS, build_profile
from simulator.scenarios.attacks import SCENARIOS
from datetime import datetime, timezone

START, DAYS = date(2026, 9, 1), 40


def make(seed=1, n=20):
    names = list(DEPARTMENTS)
    profiles = [build_profile(i, names[i % len(names)], seed) for i in range(1, n + 1)]
    return build_dataset(profiles, START, DAYS, seed)


def test_same_seed_is_identical():
    assert make(1) == make(1)


def test_different_seed_differs():
    assert make(1)[0] != make(2)[0]


def test_event_ids_unique():
    events, _ = make()
    ids = [e["event_id"] for e in events]
    assert len(ids) == len(set(ids))


def test_all_ips_valid_and_ids_match_api_pattern():
    import re
    events, _ = make()
    for e in events:
        ip_address(e["source"]["ip"])
        assert re.fullmatch(r"[A-Za-z0-9_\-]{1,64}", e["event_id"])


def test_labels_reference_real_events_and_cover_all_scenarios():
    events, labels = make()
    assert set(labels) <= {e["event_id"] for e in events}
    assert set(labels.values()) == set(SCENARIOS)


def test_attacks_only_in_last_30_percent():
    events, labels = make()
    cutoff = iso(datetime.combine(START + timedelta(days=int(DAYS * 0.7)),
                                  datetime.min.time(), tzinfo=timezone.utc))
    assert all(e["timestamp"] >= cutoff for e in events if e["event_id"] in labels)


def test_brute_force_shape():
    events, labels = make()
    failed = [e for e in events
              if labels.get(e["event_id"]) == "brute_force" and e["event_type"] == "LOGIN_FAILED"]
    assert len(failed) >= 30


def test_dormant_user_is_silent_until_activation():
    events, labels = make()
    dormant = {e["user_id"] for e in events if labels.get(e["event_id"]) == "dormant_account"}
    cutoff = iso(datetime.combine(START + timedelta(days=DORMANT_AFTER_DAYS),
                                  datetime.min.time(), tzinfo=timezone.utc))
    normal_after = [e for e in events
                    if e["user_id"] in dormant and e["event_id"] not in labels and e["timestamp"] >= cutoff]
    assert normal_after == []


def test_too_short_period_rejected():
    with pytest.raises(ValueError):
        build_dataset([build_profile(1, "Finance", 1)], START, 10, 1)