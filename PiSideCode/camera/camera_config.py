import json
from directory import cam_config_path, CAMERA_CONFIG_DIRECTORY, CALIBRATION_DIRECTORY
from pathlib import Path
from camera.camera_info import CameraInfo
import logging

logger = logging.getLogger(__name__)


def is_disabled(identifier: str):
    config_path = cam_config_path(identifier)
    try:
        # Look for config data and return it
        logger.info(f"Looking for {config_path}")
        with open(config_path, "r") as data:
            config = json.load(data)

            if config["mode"] == "DISABLED":
                return True

    except FileNotFoundError:
        logger.error("File Not Found")

    return False


def parse_config(
    identifier: str, camera_info: CameraInfo
) -> dict[str, float | str | list[int] | None]:
    config_path = cam_config_path(identifier)
    try:
        # Look for config data and return it
        logger.info(f"Looking for {config_path}")
        with open(config_path, "r") as data:
            config = json.load(data)
            return config

    except FileNotFoundError:
        logger.info("File Not Found")
        write_config(identifier, camera_info)
        return camera_info.export_configs()


# Write config data to a file following naming conventions
def write_config(identifier: str, camera_info: CameraInfo):
    Path(CAMERA_CONFIG_DIRECTORY).mkdir(parents=True, exist_ok=True)
    Path(CALIBRATION_DIRECTORY).mkdir(parents=True, exist_ok=True)

    with open(cam_config_path(identifier), "w") as file:
        json.dump(camera_info.export_configs(), file)
