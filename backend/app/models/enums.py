import enum


class AlertType(str, enum.Enum):
    EYE_CLOSURE = "EYE_CLOSURE"
    YAWN = "YAWN"
    HEAD_NOD = "HEAD_NOD"
    PHONE_USE = "PHONE_USE"
    PHONE_OBJECT = "PHONE_OBJECT"


class Severity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
