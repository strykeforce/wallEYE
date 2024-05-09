from pyrav4l2 import Device, Control
from directory import full_cam_path
import logging
import cv2
import numpy as np

BRIGHTNESS = "Brightness"
EXPOSURE = "Exposure Time, Absolute"


class CameraInfo:
    logger = logging.getLogger(__name__)

    def __init__(
        self,
        cam: cv2.VideoCapture,
        identifier: str,
        K: np.ndarray | None = None,
        D: np.ndarray | None = None,
    ):
        self.last_image: np.ndarray | None = None

        self.cam = cam
        self.identifier = identifier

        self.controller = Device(full_cam_path(identifier))

        # Modified with self.set()
        self.controls: dict[str, Control] = {
            c.name: c for c in self.controller.controls[1:]
        }
        self.valid_formats = {
            str(f): [(r.width, r.height) for r in res]
            for f, res in self.controller.available_formats.items()
        }

        curr_format = self.controller.get_format()
        self.resolution: tuple[int, int] = (curr_format[1].width, curr_format[1].height)

        self.exposure_range = self.make_control_tuple(EXPOSURE)
        self.brightness_range = self.make_control_tuple(BRIGHTNESS)

        # Calibration
        self.K = K
        self.D = D

        self.calibration_path: str | None = None

    def get_supported_resolutions(self):
        curr_format = self.controller.get_format()
        return self.valid_formats[str(curr_format[0])]

    # V4L2 Controls
    def set(self, control_name: str, value: float):
        try:
            self.controller.set_control_value(self.controls[control_name], int(value))

            CameraInfo.logger.info(
                f"{control_name} set to {value} in camera {self.identifier}"
            )

            return True

        except Exception as e:
            CameraInfo.logger.error(f"Camera {self.identifier} error: {e}")

        return False

    def get(self, control_name: str):
        self.controller.get_control_value(self.controls[control_name])

    # Util
    def make_control_tuple(self, control_name: str):
        control = self.controls[control_name]
        return (
            control.minimum,
            control.maximum,
            control.step,
        )
