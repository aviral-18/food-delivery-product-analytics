"""
Temporal demand model: growth trend, weekly seasonality, festivals, weather.

Everything here is deterministic given a numpy Generator, so the whole dataset
is reproducible from a single seed. The functions are intentionally small and
composable so the assumptions are easy to inspect and defend in an interview.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np

from app.core.constants import DayPart, FESTIVALS, Weather

# ---- Festival lookup (repeats every year) --------------------------------- #
_FESTIVAL_BY_MD: dict[tuple[int, int], dict] = {
    (f["month"], f["day"]): f for f in FESTIVALS
}


def festival_for(d: date) -> dict | None:
    return _FESTIVAL_BY_MD.get((d.month, d.day))


# ---- Day-part distribution ------------------------------------------------ #
DAY_PART_WEIGHTS: dict[DayPart, float] = {
    DayPart.BREAKFAST: 0.08,
    DayPart.LUNCH: 0.30,
    DayPart.SNACKS: 0.14,
    DayPart.DINNER: 0.40,
    DayPart.LATE_NIGHT: 0.08,
}
_DAY_PARTS = list(DAY_PART_WEIGHTS.keys())
_DAY_PART_P = np.array(list(DAY_PART_WEIGHTS.values()))
_DAY_PART_P = _DAY_PART_P / _DAY_PART_P.sum()

# Hour window per day part (start_hour, end_hour) on a 0-24 clock.
_DAY_PART_HOURS: dict[DayPart, tuple[int, int]] = {
    DayPart.BREAKFAST: (7, 10),
    DayPart.LUNCH: (12, 15),
    DayPart.SNACKS: (16, 18),
    DayPart.DINNER: (19, 22),
    DayPart.LATE_NIGHT: (22, 25),  # 24/25 wrap to next-day 00/01
}

# Contribution-margin realism: dinner & late-night baskets are larger.
DAY_PART_BASKET_MULT: dict[DayPart, float] = {
    DayPart.BREAKFAST: 0.75,
    DayPart.LUNCH: 1.0,
    DayPart.SNACKS: 0.85,
    DayPart.DINNER: 1.25,
    DayPart.LATE_NIGHT: 1.1,
}


def sample_day_part(rng: np.random.Generator) -> DayPart:
    return _DAY_PARTS[rng.choice(len(_DAY_PARTS), p=_DAY_PART_P)]


def datetime_for(rng: np.random.Generator, d: date, day_part: DayPart) -> datetime:
    """Pick a concrete order timestamp within the day-part window."""
    start, end = _DAY_PART_HOURS[day_part]
    hour = int(rng.integers(start, end))
    minute = int(rng.integers(0, 60))
    day = d
    if hour >= 24:
        hour -= 24
        day = d + timedelta(days=1)
    return datetime(day.year, day.month, day.day, hour, minute)


# ---- Weather -------------------------------------------------------------- #
def _season(month: int) -> str:
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5, 6):
        return "summer"
    if month in (7, 8, 9):
        return "monsoon"
    return "post_monsoon"  # 10, 11


# Weather distribution by season. North/central get fog in winter.
_WEATHER_WEIGHTS: dict[str, dict[Weather, float]] = {
    "winter": {Weather.CLEAR: 0.45, Weather.CLOUDY: 0.20, Weather.FOG: 0.25, Weather.RAIN: 0.10},
    "summer": {Weather.CLEAR: 0.50, Weather.EXTREME_HEAT: 0.32, Weather.CLOUDY: 0.10, Weather.RAIN: 0.08},
    "monsoon": {Weather.RAIN: 0.45, Weather.STORM: 0.12, Weather.CLOUDY: 0.25, Weather.CLEAR: 0.18},
    "post_monsoon": {Weather.CLEAR: 0.58, Weather.CLOUDY: 0.24, Weather.RAIN: 0.12, Weather.FOG: 0.06},
}


def sample_weather(rng: np.random.Generator, d: date, region: str) -> Weather:
    weights = dict(_WEATHER_WEIGHTS[_season(d.month)])
    # Fog is a northern/central winter phenomenon; drop it elsewhere.
    if Weather.FOG in weights and region not in ("north", "central"):
        weights[Weather.CLEAR] = weights.get(Weather.CLEAR, 0) + weights.pop(Weather.FOG)
    options = list(weights.keys())
    probs = np.array(list(weights.values()))
    probs = probs / probs.sum()
    return options[rng.choice(len(options), p=probs)]


# Multiplicative effect of weather on how many orders happen that day.
WEATHER_DEMAND_MULT: dict[Weather, float] = {
    Weather.CLEAR: 1.0,
    Weather.CLOUDY: 1.02,
    Weather.RAIN: 1.12,
    Weather.STORM: 0.9,          # severe storms suppress ordering
    Weather.EXTREME_HEAT: 1.06,
    Weather.FOG: 1.03,
}

# Additive minutes added to delivery time by adverse weather.
WEATHER_DELIVERY_PENALTY: dict[Weather, float] = {
    Weather.CLEAR: 0.0,
    Weather.CLOUDY: 1.0,
    Weather.RAIN: 8.0,
    Weather.STORM: 16.0,
    Weather.EXTREME_HEAT: 4.0,
    Weather.FOG: 10.0,
}


# ---- Weekly + festival demand multiplier ---------------------------------- #
_WEEKDAY_MULT = {0: 0.95, 1: 0.95, 2: 0.97, 3: 1.0, 4: 1.15, 5: 1.32, 6: 1.24}


def day_demand_multiplier(d: date, growth_index: float, weather: Weather) -> float:
    """Relative demand for a specific calendar day."""
    m = growth_index * _WEEKDAY_MULT[d.weekday()] * WEATHER_DEMAND_MULT[weather]
    fest = festival_for(d)
    if fest:
        m *= fest["multiplier"]
    return m
