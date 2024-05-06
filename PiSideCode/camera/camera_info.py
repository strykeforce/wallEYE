from pyrav4l2 import Device
from directory import fullCamPath
import logging

BRIGHTNESS = "Brightness"
EXPOSURE = "Exposure Time, Absolute"


class CameraInfo:
    logger = logging.getLogger(__name__)

    def __init__(
            self,
            cam,
            identifier,
            K=None,
            D=None):
        self.lastImage = None

        self.cam = cam
        self.identifier = identifier

        self.controller = Device(
            fullCamPath(identifier)
        )

        # Modified with self.set()
        self.controls = {c.name: c for c in self.controller.controls[1:]}
        self.validFormats = {
            str(f): [(r.width, r.height) for r in res]
            for f, res in self.controller.available_formats.items()
        }

        currFormat = self.controller.get_format()
        self.resolution = (currFormat[1].width, currFormat[1].height)

        self.exposureRange = self.makeControlTuple(EXPOSURE)
        self.brightnessRange = self.makeControlTuple(BRIGHTNESS)

        # Calibration
        self.K = K
        self.D = D

        self.calibrationPath = None

    def getSupportedResolutions(self):
        currFormat = self.controller.get_format()
        return self.validFormats[str(currFormat[0])]

    # V4L2 Controls
    def set(self, controlName, value):
        try:
            self.controller.set_control_value(
                self.controls[controlName], int(value))

            CameraInfo.logger.info(
                f"{controlName} set to {value} in camera {self.identifier}")
            
            return True

        except Exception as e:
            CameraInfo.logger.error(f"Camera {self.identifier} error: {e}")

        return False

    def get(self, controlName):
        self.controller.get_control_value(self.controls[controlName])

    # Util
    def makeControlTuple(self, controlName):
        control = self.controls[controlName]
        return (
            control.minimum,
            control.maximum,
            control.step,
        )
