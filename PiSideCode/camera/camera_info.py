from pyrav4l2 import Device
from directory import fullCamPath
import logging

class CameraInfo:
    logger = logging.getLogger(__name__)

    def __init__(
        self, cam, identifier, supportedResolutions, resolution=None, K=None, D=None
    ):
        self.lastImage = None

        self.cam = cam
        self.identifier = identifier
        self.resolution = resolution
        self.supportedResolutions = supportedResolutions
        self.exposureRange = (0, 100, 1)
        self.brightnessRange = (0, 240, 1)
        self.validFormats = []

        # Calibration
        self.K = K
        self.D = D

        self.calibrationPath = None

        self.controller = Device(
            fullCamPath(identifier)
        )

        self.controls = dict(
            zip(
                list(map(lambda control: control.name, self.controller.controls[1:])),
                self.controller.controls[1:],
            )
        )

    def set(self, controlName, value):
        try:
            self.controller.set_control_value(self.controls[controlName], value)

            if self.get(controlName) == value:
                CameraInfo.logger.info(f"Successfully set {controlName} = {value} in camera {self.identifier}")
        
        except Exception as e:
            CameraInfo.logger.error(f"Camera {self.identifier} error: {e}")
        
        return False

    def get(self, controlName):
        self.controller.get_control_value(controlName)
