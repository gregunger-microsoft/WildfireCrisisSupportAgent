"""Simulate Update logic — mutate a payload to mimic streaming updates."""
from __future__ import annotations

import copy
import random
from datetime import datetime, timedelta, timezone

from wildfire_crisis_demo.domain.models import WildfireIncidentBundle


def simulate_update(bundle: WildfireIncidentBundle) -> WildfireIncidentBundle:
    """Return a mutated copy simulating a real-time feed update."""
    data = bundle.model_dump()
    now = datetime.now(timezone.utc)

    # Wind shift
    if data["weather_feed"]:
        w = data["weather_feed"][-1]
        w["wind_speed_mph"] = round(w["wind_speed_mph"] + random.uniform(2, 8), 1)
        w["wind_direction"] = random.choice(["NW", "N", "NE", "W"])
        w["timestamp_utc"] = now.isoformat()
        w["summary"] = f"Wind shifted to {w['wind_direction']} at {w['wind_speed_mph']} mph"

    # Fire growth
    if data["fire_behavior"]:
        fb = data["fire_behavior"][-1]
        fb["perimeter_acres"] = round(fb["perimeter_acres"] * random.uniform(1.05, 1.15), 1)
        fb["containment_pct"] = max(0, round(fb["containment_pct"] - random.uniform(1, 5), 1))
        fb["timestamp_utc"] = now.isoformat()

    # AQI increase
    if data["air_quality"]:
        aq = data["air_quality"][-1]
        aq["aqi"] = min(500, aq["aqi"] + random.randint(10, 30))
        aq["timestamp_utc"] = now.isoformat()

    # Shelter occupancy increase
    if data["shelters"]:
        s = data["shelters"][0]
        s["current_occupancy"] = min(s["capacity"], s["current_occupancy"] + random.randint(5, 20))

    return WildfireIncidentBundle.model_validate(data)
