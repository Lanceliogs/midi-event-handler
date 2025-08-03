import logging
import logging.config
import yaml
from pathlib import Path
from os import getenv

config_path = Path(
        getenv("MEH_LOG_CONFIG", "config.yaml")
    )

if config_path.exists():
    with config_path.open("r") as f:
        config: dict = yaml.safe_load(f)
        logging.config.dictConfig(config.get("logging"))
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def get_logger(name: str = "meh-app") -> logging.Logger:
    """
    Returns a configured logger instance.
    Initializes the logger once using the YAML config file.
    """
    return logging.getLogger(name)

