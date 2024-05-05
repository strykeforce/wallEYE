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

# if __name__ == "__main__":
#     from pyrav4l2 import Device

#     dev = Device(
#         os.path.join("/dev/v4l/by-path", "pci-0000:04:00.0-usb-0:1:1.0-video-index0")
#     )

#     print(f"Device name: {dev.device_name}")
#     print(f"Driver name: {dev.driver_name}")
#     if dev.is_video_capture_capable:
#         print(f"Device supports video capturing")
#     else:
#         print(f"Device does not support video capturing")

#     color_format, frame_size = dev.get_format()
#     print(f"Color format: {color_format}")
#     print(f"Frame size: {frame_size}")

#     available_formats = dev.available_formats

#     for color_format in available_formats.keys():
#         print(f"{color_format}:")
#         for frame_size in available_formats[color_format]:
#             print(f"    {frame_size}")
#         print()

#     color_format = list(available_formats.keys())[0]
#     frame_size = available_formats[color_format][0]
#     print(type(color_format), type(frame_size))
#     dev.set_format(color_format, frame_size)

#     available_controls = dev.controls
#     print(list(map(lambda x: x.name, available_controls)))
#     for control in available_controls:
#         print(control.name)
#         dev.reset_control_to_default(control)

#     test = dict(zip(list(map(lambda x: x.name, available_controls[1:])), available_controls[1:]))
#     print(test)
    
