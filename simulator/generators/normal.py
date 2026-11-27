import random
from datetime import date, datetime, timedelta, timezone

from simulator.generators.common import IdFactory, make_event
from simulator.generators.employees import Profile


def generate_day(p: Profile, day: date, seed: int) -> list[dict]:
    rng = random.Random(f"{seed}:{p.user_id}:{day.isoformat()}")
    if day.weekday() >= 5 or rng.random() < 0.03:  # weekends and the odd sick day
        return []

    ids = IdFactory(f"sim{seed}_{p.user_id}_{day:%Y%m%d}")
    midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    login = midnight + timedelta(hours=p.start_hour, minutes=rng.randint(0, 45))
    logout = login + timedelta(hours=p.work_hours, minutes=rng.randint(-20, 30))
    span = (logout - login).total_seconds()
    device = rng.choice(p.devices)
    meta = {"country": p.country}

    def at() -> datetime:
        return login + timedelta(seconds=rng.uniform(60, span - 60))

    events = []
    if rng.random() < 0.04:  # a typo'd password before logging in
        events.append(make_event(
            ids.next(), p.user_id, "LOGIN_FAILED",
            login - timedelta(seconds=rng.randint(20, 90)), p.home_ip, device, metadata=meta,
        ))
    events.append(make_event(ids.next(), p.user_id, "LOGIN_SUCCESS", login, p.home_ip, device, metadata=meta))

    for _ in range(rng.randint(*p.daily_files)):
        events.append(make_event(
            ids.next(), p.user_id, "FILE_ACCESS", at(), p.home_ip, device,
            resource=("document", f"doc_{rng.randint(1, 500)}"),
            metadata={"department": p.department},
        ))
    for _ in range(rng.randint(*p.daily_downloads)):
        size = min(rng.expovariate(1 / p.avg_download_mb), p.avg_download_mb * 6)
        events.append(make_event(
            ids.next(), p.user_id, "FILE_DOWNLOAD", at(), p.home_ip, device,
            resource=("document", f"doc_{rng.randint(1, 500)}"),
            metadata={"file_size_mb": max(0.1, round(size, 2)), "department": p.department},
        ))

    events.append(make_event(ids.next(), p.user_id, "LOGOUT", logout, p.home_ip, device, metadata=meta))
    return events


def generate_normal(profiles: list[Profile], start: date, days: int, seed: int) -> list[dict]:
    events: list[dict] = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        for p in profiles:
            events.extend(generate_day(p, day, seed))
    return events