import json

def parseConfig(usbIndex):
    try:
        with open(f"./Camera/CameraConfigs/ConfigSettings{usbIndex}.json", 'r') as data:
            config = json.load(data)
            return config

    except FileNotFoundError:
        print("File Not Found")
        fileDump = {
            "Resolution" : None,
            "Gain" : None,
            "Exposure" : None
        }

        with open(f"./Camera/CameraConfigs/ConfigSettings{usbIndex}.json", 'w') as outFile:
            json.dump(fileDump, outFile)
        return fileDump

def writeConfig(usbIndex, resolution, gain, exposure):
    with open(f"./Camera/CameraConfigs/ConfigSettings{usbIndex}.json", 'w') as data:
        fileDump = {"Resolution" : resolution, "Gain" : gain, "Exposure" : exposure}
        json.dump(fileDump, data)



