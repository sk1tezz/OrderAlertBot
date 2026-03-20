from enum import StrEnum


class OrderStatus(StrEnum):
    ACTIVE = "active"
    UPCOMING = "upcoming"
    OVERDUE = "overdue"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReminderType(StrEnum):
    H24 = "24h"
    H3 = "3h"
    H1 = "1h"
    DEADLINE = "deadline"
    OVERDUE = "overdue"
