import os.path

V4L_PATH = "/dev/v4l/by-path"
CONFIG_DATA_PATH = "config_data/system_data.json"
LOG = "walleye.log"
CONFIG_ZIP = "config.zip"


def cleanIdentifier(identifier):
    return identifier.replace(":", "-").replace(".", "-")


def calibrationImageFolder(identifier):
    return os.path.join("config_data", f"cam_{cleanIdentifier(identifier)}_cal_imgs")


def calibrationPathByCam(identifier, resolution):
    return os.path.join(
        "config_data",
        "calibrations",
        f"cam_{cleanIdentifier(identifier)}_{resolution}_cal_data.json",
    )


def camConfigPath(identifier):
    return os.path.join(
        "config_data",
        "camera_configs",
        f"config_settings_{cleanIdentifier(identifier)}.json",
    )


def fullCamPath(identifier):
    return os.path.join(V4L_PATH, identifier)
