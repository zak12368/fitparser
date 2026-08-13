"""Constants and sport/sub-sport mapping for Apple Watch workout types.

The Apple Watch FIT export stores sport and sub_sport as strings in the
session message. This module maps every known (sport, sub_sport) pair to
a human-readable workout label.
"""

from typing import Final

# Apple Watch stores cadence as half-strides (per-leg), multiply by 2.
CADENCE_MULTIPLIER: Final[int] = 2

# HR zone thresholds as percentage of max HR.
# Zone 1: <60%  Zone 2: 60-69%  Zone 3: 70-79%  Zone 4: 80-89%  Zone 5: ≥90%
HR_ZONE_THRESHOLDS: Final[list[int]] = [60, 70, 80, 90]


WORKOUT_MAP: dict[tuple[str, str], str] = {
    # Running
    ("running", "generic"): "Outdoor Run",
    ("running", "indoor_running"): "Indoor Run",
    # Walking
    ("walking", "generic"): "Outdoor Walk",
    ("walking", "indoor_walking"): "Indoor Walk",
    # Cycling
    ("cycling", "road_cycling"): "Outdoor Cycling",
    ("cycling", "mountain_cycling"): "Mountain Cycling",
    ("cycling", "indoor_cycling"): "Indoor Cycling",
    # Fitness Equipment (always indoor)
    ("fitness_equipment", "elliptical"): "Indoor Elliptical",
    ("fitness_equipment", "indoor_rowing"): "Indoor Rower",
    ("fitness_equipment", "other_cardio"): "Indoor Cardio",
    # Swimming
    ("swimming", "pool_swimming"): "Pool Swim",
    ("swimming", "open_water_swimming"): "Open Water Swim",
    # HIIT / Strength / Yoga
    ("hiit", "generic"): "HIIT",
    ("yoga", "generic"): "Yoga",
    ("core_training", "generic"): "Core Training",
    ("functional_strength_training", "generic"): "Functional Strength Training",
    ("training", "strength_training"): "Strength Training",
    ("mind_and_body", "generic"): "Mind and Body",
    ("mind_and_body", "yoga"): "Yoga",
    # Hiking
    ("hiking", "generic"): "Hiking",
    # Apple Watch numeric sport IDs (fallback for non-standard sports)
    # 53 = Dive (Apple Watch)
    ("53", "generic"): "Dive",
    # 62/70 = HIIT (Apple Watch)
    ("62", "70"): "HIIT",
    # Generic fallback
    ("generic", "generic"): "Other Workout",
}
