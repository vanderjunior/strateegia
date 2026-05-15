from __future__ import annotations


def clamp_value(
    value: float | int | None,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    if value is None:
        return minimum
    return max(minimum, min(float(value), maximum))


def average_values(
    values: list[float | int | None],
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    if not values:
        return minimum
    clamped_values = [clamp_value(value, minimum, maximum) for value in values]
    return round(clamp_value(sum(clamped_values) / len(clamped_values), minimum, maximum), 4)


def state_reasoning(prefix: str, state: str, details: list[str]) -> list[str]:
    return [f"{prefix}: {state}.", *details]


def state_message(state: str, mapping: dict[str, str], fallback: str) -> str:
    return mapping.get(state, fallback)
