import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "Sistema de Control de Cansancio en Choferes"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/somnolence",
    )

    # MQTT
    MQTT_BROKER: str = os.getenv("MQTT_BROKER", "localhost")
    MQTT_PORT: int = int(os.getenv("MQTT_PORT", "1883"))
    MQTT_TOPIC_PREFIX: str = os.getenv("MQTT_TOPIC_PREFIX", "somnolence")

    # Alert notification thresholds (RF8)
    ALERT_THRESHOLD_COUNT: int = int(os.getenv("ALERT_THRESHOLD_COUNT", "5"))
    ALERT_THRESHOLD_WINDOW_MINUTES: int = int(os.getenv("ALERT_THRESHOLD_WINDOW_MINUTES", "10"))

    # CORS — se lee de env var (CSV) para poder agregar la IP del frontend sin rebuild
    CORS_ORIGINS: list = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://frontend:3000",
        ).split(",")
        if o.strip()
    ]

    # JWT / Auth
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me-in-prod")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_MINUTES: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))


settings = Settings()
