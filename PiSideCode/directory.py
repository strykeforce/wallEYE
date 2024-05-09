import os.path

V4L_PATH = "/dev/v4l/by-path"
CONFIG_DATA_PATH = "config_data/system_data.json"
LOG = "walleye.log"
CONFIG_ZIP = "config.zip"


def clean_identifier(identifier: str) -> str:
    return identifier.replace(":", "-").replace(".", "-")


def calibration_image_folder(identifier: str) -> str:
    return os.path.join("config_data", f"cam_{clean_identifier(identifier)}_cal_imgs")


def calibration_path_by_cam(identifier: str, resolution: tuple[int, int]) -> str:
    return os.path.join(
        "config_data",
        "calibrations",
        f"cam_{clean_identifier(identifier)}_{resolution}_cal_data.json",
    )


def cam_config_path(identifier: str) -> str:
    return os.path.join(
        "config_data",
        "camera_configs",
        f"config_settings_{clean_identifier(identifier)}.json",
    )


def full_cam_path(identifier: str) -> str:
    return os.path.join(V4L_PATH, identifier)
