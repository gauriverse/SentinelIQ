import random
from datetime import date, datetime, timedelta, timezone

from simulator.generators.common import IdFactory, iso
from simulator.generators.employees import Profile
from simulator.generators.normal import generate_normal
from simulator.scenarios.attacks import SCENARIOS

DORMANT_AFTER_DAYS = 10  # dormant victims stop all activity after this many days


def build_dataset(
    profiles: list[Profile],
    start: date,
    days: int,
    seed: int,
    victims_per_scenario: int = 3,
) -> tuple[list[dict], dict[str, str]]:
    """Returns (events sorted by time, labels mapping event_id -> scenario)."""
    if days < 20:
        raise ValueError("days must be at least 20 (clean history is needed before attacks)")

    rng = random.Random(f"{seed}:plan")
    events = generate_normal(profiles, start, days, seed)

    k = min(len(profiles), victims_per_scenario * len(SCENARIOS))
    victims = rng.sample(profiles, k)
    per = max(1, k // len(SCENARIOS))
    labels: dict[str, str] = {}
    attack_events: list[dict] = []
    first_attack_day = int(days * 0.7)  # attacks only in the last 30% of the timeline

    for i, (name, (generator, hour)) in enumerate(SCENARIOS.items()):
        for p in victims[i * per:(i + 1) * per]:
            day = start + timedelta(days=rng.randint(first_attack_day, days - 1))
            when = datetime(day.year, day.month, day.day, hour, rng.randint(0, 59), tzinfo=timezone.utc)
            ids = IdFactory(f"atk{seed}_{name}_{p.user_id}")
            for e in generator(p, when, rng, ids):
                labels[e["event_id"]] = name
                attack_events.append(e)
            if name == "dormant_account":
                cutoff = iso(datetime.combine(start + timedelta(days=DORMANT_AFTER_DAYS),
                                              datetime.min.time(), tzinfo=timezone.utc))
                events = [e for e in events if not (e["user_id"] == p.user_id and e["timestamp"] >= cutoff)]

    all_events = events + attack_events
    all_events.sort(key=lambda e: (e["timestamp"], e["event_id"]))
    return all_events, labels