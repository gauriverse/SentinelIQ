import random
from datetime import datetime, timedelta

from simulator.generators.common import IdFactory, make_event
from simulator.generators.employees import Profile

# RFC 5737 documentation ranges: guaranteed not to be real hosts.
TEST_NETS = ["203.0.113", "198.51.100", "192.0.2"]


def _external_ip(rng: random.Random) -> str:
    return f"{rng.choice(TEST_NETS)}.{rng.randint(1, 254)}"


def brute_force(p: Profile, when: datetime, rng: random.Random, ids: IdFactory) -> list[dict]:
    """Dozens of failed logins from one external IP in minutes, then a success."""
    ip, events, t = _external_ip(rng), [], when
    for _ in range(rng.randint(30, 60)):
        t += timedelta(seconds=rng.uniform(2, 5))
        events.append(make_event(ids.next(), p.user_id, "LOGIN_FAILED", t, ip, "unknown_device",
                                 metadata={"country": "RO"}))
    t += timedelta(seconds=5)
    events.append(make_event(ids.next(), p.user_id, "LOGIN_SUCCESS", t, ip, "unknown_device",
                             metadata={"country": "RO"}))
    return events


def exfiltration(p: Profile, when: datetime, rng: random.Random, ids: IdFactory) -> list[dict]:
    """After-hours login on a new device, mass file access, huge downloads, USB device."""
    device, t, events = f"dev_{p.user_id:04d}_new", when, []
    meta = {"country": p.country}
    events.append(make_event(ids.next(), p.user_id, "LOGIN_SUCCESS", t, p.home_ip, device, metadata=meta))
    for _ in range(rng.randint(60, 120)):
        t += timedelta(seconds=rng.uniform(2, 8))
        events.append(make_event(ids.next(), p.user_id, "FILE_ACCESS", t, p.home_ip, device,
                                 resource=("document", f"doc_{rng.randint(1, 500)}"),
                                 metadata={"department": p.department}))
    for _ in range(rng.randint(12, 20)):
        t += timedelta(seconds=rng.uniform(20, 60))
        events.append(make_event(ids.next(), p.user_id, "FILE_DOWNLOAD", t, p.home_ip, device,
                                 resource=("document", f"doc_{rng.randint(1, 500)}"),
                                 metadata={"file_size_mb": round(rng.uniform(80, 400), 1),
                                           "department": p.department}))
    t += timedelta(minutes=1)
    events.append(make_event(ids.next(), p.user_id, "USB_CONNECT", t, p.home_ip, device,
                             resource=("usb", f"usb_{rng.randint(1, 9)}"), metadata=meta))
    t += timedelta(minutes=2)
    events.append(make_event(ids.next(), p.user_id, "LOGOUT", t, p.home_ip, device, metadata=meta))
    return events


def dormant_activation(p: Profile, when: datetime, rng: random.Random, ids: IdFactory) -> list[dict]:
    """A long-silent account wakes up at night: external login, privilege change, bulk access."""
    ip, t, events = _external_ip(rng), when, []
    meta = {"country": "VN"}
    events.append(make_event(ids.next(), p.user_id, "LOGIN_SUCCESS", t, ip, "unknown_device", metadata=meta))
    t += timedelta(minutes=2)
    events.append(make_event(ids.next(), p.user_id, "PERMISSION_CHANGE", t, ip, "unknown_device",
                             resource=("role", "admin"), metadata={"new_role": "admin"}))
    for _ in range(rng.randint(5, 10)):
        t += timedelta(seconds=rng.uniform(10, 40))
        events.append(make_event(ids.next(), p.user_id, "RESOURCE_ACCESS", t, ip, "unknown_device",
                                 resource=("database", f"db_{rng.choice(['hr', 'finance', 'crm'])}"),
                                 metadata=meta))
    for _ in range(rng.randint(100, 200)):
        t += timedelta(seconds=rng.uniform(1, 3))
        events.append(make_event(ids.next(), p.user_id, "FILE_ACCESS", t, ip, "unknown_device",
                                 resource=("document", f"doc_{rng.randint(1, 500)}"), metadata=meta))
    return events


def impossible_travel(p: Profile, when: datetime, rng: random.Random, ids: IdFactory) -> list[dict]:
    """Two successful logins from different continents minutes apart."""
    device = p.devices[0]
    first = make_event(ids.next(), p.user_id, "LOGIN_SUCCESS", when, p.home_ip, device,
                       metadata={"country": p.country})
    second = make_event(ids.next(), p.user_id, "LOGIN_SUCCESS",
                        when + timedelta(minutes=rng.randint(5, 12)),
                        _external_ip(rng), "unknown_device", metadata={"country": "BR"})
    return [first, second]


# name -> (generator, hour of day (UTC) when it starts)
SCENARIOS = {
    "brute_force": (brute_force, 3),
    "exfiltration": (exfiltration, 2),
    "dormant_account": (dormant_activation, 3),
    "impossible_travel": (impossible_travel, 12),
}