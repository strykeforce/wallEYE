import json

def parseConfig(camPath):
    try:
        with open(f"./Camera/CameraConfigs/ConfigSettings_{camPath}.json", 'r') as data:
            config = json.load(data)
            return config

    except FileNotFoundError:
        print("File Not Found")
        fileDump = {
            "Resolution" : None,
            "Gain" : None,
            "Exposure" : None,
        }

        with open(f"./Camera/CameraConfigs/ConfigSettings_{camPath}.json", 'w') as outFile:
            json.dump(fileDump, outFile)
        return fileDump

def writeConfig(camPath, resolution, gain, exposure, calibrationPath = None):
    with open(f"./Camera/CameraConfigs/ConfigSettings_{camPath}.json", 'w') as data:
        fileDump = {"Resolution" : resolution, "Gain" : gain, "Exposure" : exposure}
        json.dump(fileDump, data)



