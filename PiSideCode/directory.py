import os.path
import pathlib

PARENT = "walleye_data"

V4L_PATH = "/dev/v4l/by-path"
CONFIG_DIRECTORY = os.path.join(PARENT, "config_data")
CAMERA_CONFIG_DIRECTORY = os.path.join(CONFIG_DIRECTORY, "camera_configs")
CALIBRATION_DIRECTORY = os.path.join(CONFIG_DIRECTORY, "calibrations")
CONFIG_DATA_PATH = os.path.join(CONFIG_DIRECTORY, "system_data.json")
LOG = os.path.join(PARENT, "walleye.log")
CONFIG_ZIP = os.path.join(PARENT, "config.zip")
TAG_LAYOUT_PATH = os.path.join(CONFIG_DIRECTORY, "april_tag_layout.json")
FALLBACK_TAG_LAYOUT_PATH = os.path.join("processing", "april_tag_layout.json")

pathlib.Path(CONFIG_DIRECTORY).mkdir(parents=True, exist_ok=True)

def clean_identifier(identifier: str) -> str:
    return identifier.replace(":", "-").replace(".", "-")


def calibration_image_folder(identifier: str) -> str:
    return os.path.join(CONFIG_DIRECTORY, f"cam_{clean_identifier(identifier)}_cal_imgs")


def calibration_path_by_cam(identifier: str, resolution: tuple[int, int]) -> str:
    return os.path.join(
        CALIBRATION_DIRECTORY,
        f"cam_{clean_identifier(identifier)}_{resolution}_cal_data.json",
    )


def cam_config_path(identifier: str) -> str:
    return os.path.join(
        CAMERA_CONFIG_DIRECTORY,
        f"config_settings_{clean_identifier(identifier)}.json",
    )


def full_cam_path(identifier: str) -> str:
    return os.path.join(V4L_PATH, identifier)
