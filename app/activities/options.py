from enum import IntEnum, StrEnum


class ActivityType(StrEnum):
    WORK = "work"
    EXERCISE = "exercise"
    MEAL = "meal"
    BREAK = "break"
    SLEEP = "sleep"
    OTHER = "other"

class EaseRating(IntEnum):
    VERY_DIFFICULT = 1
    DIFFICULT = 2
    NORMAL = 3
    EASY = 4
    EFFORTLESS = 5

EASE_LABELS = {
    EaseRating.VERY_DIFFICULT: "Extremely difficult",
    EaseRating.DIFFICULT: "Difficult",
    EaseRating.NORMAL: "Normal effort",
    EaseRating.EASY: "Relatively easy",
    EaseRating.EFFORTLESS: "Effortless / natural flow",
}

EASE_RATING_ACTIVITY_TYPES = {ActivityType.WORK}