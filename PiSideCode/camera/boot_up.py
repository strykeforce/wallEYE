import json
from directory import cam_config_path, CAMERA_CONFIG_DIRECTORY, CALIBRATION_DIRECTORY
from pathlib import Path


def parse_config(identifier: str) -> dict[str, float | str | list[int] | None]:
    config_path = cam_config_path(identifier)
    try:
        # Look for config data and return it
        print(f"Looking for {config_path}")
        with open(config_path, "r") as data:
            config = json.load(data)
            return config

    except FileNotFoundError:
        print("File Not Found")
        file_dump = {
            "Resolution": None,
            "Brightness": None,
            "Exposure": None,
        }

        with open(config_path, "w") as outFile:
            json.dump(file_dump, outFile)
        return file_dump


# Write config data to a file following naming conventions
def write_config(
    identifier: str, resolution: tuple[int, int], brightness: float, exposure: float
):
    Path(CAMERA_CONFIG_DIRECTORY).mkdir(parents=True, exist_ok=True)
    Path(CALIBRATION_DIRECTORY).mkdir(parents=True, exist_ok=True)

    with open(cam_config_path(identifier), "w") as data:
        file_dump = {
            "Resolution": resolution,
            "Brightness": brightness,
            "Exposure": exposure,
        }
        json.dump(file_dump, data)
