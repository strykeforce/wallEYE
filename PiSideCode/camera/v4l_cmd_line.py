import subprocess
from directory import fullCamPath
import re
import os

def getFormats(identifier):
    formatParams = subprocess.run(
        [
            "v4l2-ctl",
            "-d",
            fullCamPath(identifier),
            "--list-formats-ext",
        ],
        capture_output=True,
    ).stdout.decode("utf-8")

    supportedResolutions = sorted(
        list(
            set(  # Unique values
                map(
                    lambda x: (
                        int(x.split("x")[0]),
                        int(x.split("x")[1]),
                    ),
                    re.findall(
                        "[0-9]+x[0-9]+",
                        formatParams,
                    ),
                )
            )
        )
    )

    formats = set(
        map(
            lambda x: re.search("'....'", x).group().strip("'"),
            re.findall(
                ": '....'",
                formatParams,
            ),
        )
    )

    return supportedResolutions, formats


def getSettings(identifier):
    settingParams = subprocess.run(
        ["v4l2-ctl", "-d", fullCamPath(identifier), "--list-ctrls-menus"],
        capture_output=True,
    ).stdout.decode("utf-8")

    try:
        exposureRange = tuple(
            map(
                lambda x: int(x.split("=")[-1]),
                re.search(
                    "exposure_absolute .* min=-?[0-9]+ max=-?[0-9]+ step=[0-9]+",
                    settingParams,
                )
                .group()
                .split()[-3:],
            )
        )
    except AttributeError:
        exposureRange = [0, 0, 0]

    brightnessRange = tuple(
        map(
            lambda x: int(x.split("=")[-1]),
            re.search(
                "brightness .* min=-?[0-9]+ max=-?[0-9]+ step=[0-9]+",
                settingParams,
            )
            .group()
            .split()[-3:],
        )
    )

    return exposureRange, brightnessRange

# Use methods in Cameras, do not use directly
def setBrightness(identifier, brightness):
    return os.system(
        f"v4l2-ctl -d {fullCamPath(identifier)} --set-ctrl brightness={brightness}"
    )

def setExposure(identifier, exposure):
    return os.system(
        f"v4l2-ctl -d {fullCamPath(identifier)} --set-ctrl exposure_absolute={exposure}"  #  --set-ctrl exposure_auto=1
    )
###