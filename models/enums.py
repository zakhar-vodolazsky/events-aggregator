from enum import StrEnum


class EventStatus(StrEnum):
    PUBLISHED = "published"
    ARCHIVED = "archived"
    CANCELED = "canceled"
