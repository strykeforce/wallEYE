import json
from directory import camConfigPath

def parseConfig(identifier):
    configPath = camConfigPath(identifier)
    try:
        # Look for config data and return it
        print(f"Looking for {configPath}")
        with open(configPath, "r") as data:
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
            configPath, "w"
        ) as outFile:
            json.dump(fileDump, outFile)
        return fileDump


# Write config data to a file following naming conventions
def writeConfig(identifier, resolution, brightness, exposure):
    with open(camConfigPath(identifier), "w") as data:
        fileDump = {
            "Resolution": resolution,
            "Brightness": brightness,
            "Exposure": exposure,
        }
        json.dump(fileDump, data)
