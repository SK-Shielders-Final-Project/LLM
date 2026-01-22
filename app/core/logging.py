import logging

from app.core.settings import Settings


def ConfigureLogging(settings: Settings) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.info("Booting %s", settings.app_name)
