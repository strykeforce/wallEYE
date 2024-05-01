import json


def parseConfig(camPath):
    try:
        # Look for config data and return it
        print(f"Looking for ./Camera/CameraConfigs/ConfigSettings_{camPath}.json")
        with open(f"./Camera/CameraConfigs/ConfigSettings_{camPath}.json", "r") as data:
            config = json.load(data)
            return config

    except FileNotFoundError:
        print("File Not Found")
        fileDump = {
            "Resolution": None,
            "Brightness": None,
            "Exposure": None,
        }

        with open(
            f"./Camera/CameraConfigs/ConfigSettings_{camPath}.json", "w"
        ) as outFile:
            json.dump(fileDump, outFile)
        return fileDump


# Write config data to a file following naming conventions
def writeConfig(camPath, resolution, brightness, exposure):
    with open(f"./Camera/CameraConfigs/ConfigSettings_{camPath}.json", "w") as data:
        fileDump = {
            "Resolution": resolution,
            "Brightness": brightness,
            "Exposure": exposure,
        }
        json.dump(fileDump, data)
