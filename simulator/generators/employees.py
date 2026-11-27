import random
from dataclasses import dataclass

# per-department behaviour: (files/day), (downloads/day), average download size in MB
DEPARTMENTS: dict[str, dict] = {
    "Engineering": {"files": (20, 60), "downloads": (5, 15), "avg_mb": 2.5},
    "Finance":     {"files": (15, 45), "downloads": (5, 12), "avg_mb": 3.0},
    "HR":          {"files": (10, 30), "downloads": (3, 10), "avg_mb": 1.5},
    "Sales":       {"files": (10, 35), "downloads": (4, 12), "avg_mb": 2.0},
    "Support":     {"files": (15, 40), "downloads": (3, 10), "avg_mb": 1.0},
}


@dataclass(frozen=True)
class Profile:
    user_id: int
    department: str
    start_hour: int          # UTC login hour
    work_hours: int
    home_ip: str
    devices: tuple[str, ...]
    country: str
    daily_files: tuple[int, int]
    daily_downloads: tuple[int, int]
    avg_download_mb: float


def build_profile(user_id: int, department: str, seed: int) -> Profile:
    rng = random.Random(f"{seed}:profile:{user_id}")
    cfg = DEPARTMENTS.get(department) or DEPARTMENTS["Support"]
    dept_idx = list(DEPARTMENTS).index(department) if department in DEPARTMENTS else 4
    n_devices = rng.choice([1, 1, 2])
    return Profile(
        user_id=user_id,
        department=department,
        start_hour=rng.randint(8, 10),
        work_hours=rng.randint(8, 9),
        home_ip=f"10.{dept_idx}.{rng.randint(0, 255)}.{rng.randint(1, 254)}",
        devices=tuple(f"dev_{user_id:04d}_{c}" for c in "ab"[:n_devices]),
        country="IN",
        daily_files=cfg["files"],
        daily_downloads=cfg["downloads"],
        avg_download_mb=cfg["avg_mb"] * rng.uniform(0.8, 1.2),
    )