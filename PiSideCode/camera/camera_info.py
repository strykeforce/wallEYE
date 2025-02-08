from pyrav4l2 import (
    Device,
    Control,
    Menu,
)
import logging
import cv2
import numpy as np
import re
import json
from enum import Enum
import time
from threading import Lock
from directory import  full_cam_path


class Modes(Enum):
    POSE_ESTIMATION = "POSE_ESTIMATION"
    TAG_SERVOING = "TAG_SERVOING"
    DISABLED = "DISABLED"


EXPOSED_PROPERTIES = re.compile(
    "[Bb]rightness|[Exposure \(Auto\)]|[Exposure Time, Absolute]|[Exposure, Auto]|[Exposure \(Absolute\)]|Contrast|Saturation|Gamma|Gain"
)


class CameraInfo:
    logger = logging.getLogger(__name__)

    def __init__(
        self,
        cam: cv2.VideoCapture,
        identifier: str,
        K: np.ndarray | None = None,
        D: np.ndarray | None = None,
    ):
        self.cam = cam
        self.identifier = identifier
        self.mode: Modes = Modes.POSE_ESTIMATION
        self.setting_lock = Lock()

        self.controller = Device(full_cam_path(identifier))

        # Modified with self.set()
        self.controls: dict[str, Control] = {
            c.name: c
            for c in self.controller.controls
            if EXPOSED_PROPERTIES.match(c.name)
        }

        CameraInfo.logger.info(
            "All Controls: " + str([c.name for c in self.controller.controls])
        )
        CameraInfo.logger.info(f"Valid Controls: {list(self.controls)}")

        self.valid_formats = {
            str(f): [(r.width, r.height) for r in res]
            for f, res in self.controller.available_formats.items()
        }
        self.valid_color_formats = {
            str(f): f for f in self.controller.available_formats
        }

        self.get_format()

        # Calibration
        self.K = K
        self.D = D

        self.calibration_path: str | None = None

    def get_supported_resolutions(self):
        try:
            curr_format = self.controller.get_format()
        except FileNotFoundError:
            CameraInfo.logger.fatal(f"Camera {self.identifier} disconnected. Cannot read information.")
            
        return self.valid_formats[str(curr_format[0])]

    def set_color_format(self, color_format: str) -> bool:
        success = self.set_format(color_format, self.resolution)

        CameraInfo.logger.info(
            f"Supported resolutions: {self.get_supported_resolutions()}"
        )
        CameraInfo.logger.info(f"Supported formats: {list(self.valid_formats.keys())}")

        CameraInfo.logger.info(f"Supported fps: {list(self.valid_frame_rates.keys())}")

        return success

    def set_resolution(self, resolution: tuple[int, int]) -> bool:
        return self.set_format(self.color_format, resolution)

    def set_format(self, color_format: str, resolution: tuple[int, int]) -> bool:
        if self.cam is None:
            return False
        try:
            if color_format != self.color_format and resolution not in self.valid_formats[color_format]:
                resolution = self.valid_formats[color_format][0]
            self.cam.set(
                cv2.CAP_PROP_FOURCC,
                self.valid_color_formats[color_format].pixelformat,
            )
            self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            self.cam.set(
                cv2.CAP_PROP_FRAME_HEIGHT,
                resolution[1],
            )

            time.sleep(1)
            self.get_format()

            CameraInfo.logger.info(
                f"Format set to {self.color_format} at {self.resolution} in camera {self.identifier} at {self.frame_rate} fps, wanted {color_format} at {resolution}"
            )

            return color_format == self.color_format and resolution == self.resolution

        except Exception as e:
            CameraInfo.logger.error(f"Camera {self.identifier} error: {e}")

        return False

    def set_frame_rate(self, frame_rate: int):
        if self.cam is None:
            return False
        try:
            
            # self.controller.set_frame_interval(self.valid_frame_rates[frame_rate])
            self.cam.set(cv2.CAP_PROP_FPS, frame_rate)
            time.sleep(1)

            self.get_format()

            CameraInfo.logger.info(
                f"Frame rate set to {self.frame_rate} in camera {self.identifier}, wanted {frame_rate}"
            )

            return self.frame_rate == frame_rate

        except Exception as e:
            CameraInfo.logger.error(f"Camera {self.identifier} error: {e}")

        return False

    def set(self, control_name: str, value: int | str) -> bool:
        if self.cam is None:
            return False
        if control_name not in self.controls:
            CameraInfo.logger.error(
                f"{control_name} is not available for camera {self.identifier}"
            )
            return False

        try:
            control = self.controls[control_name]

            if isinstance(control, Menu):
                value = next(
                    filter(lambda menu_item: menu_item.name == value, control.items)
                )
            else:
                value = int(value)

            self.controller.set_control_value(self.controls[control_name], value)

            CameraInfo.logger.info(
                f"{control_name} set to {value} in camera {self.identifier} (actually {self.get(control_name)})"
            )

            return True

        except Exception as e:
            CameraInfo.logger.error(f"Camera {self.identifier} error: {e}")

        return False

    def get(self, control_name: str):
        return self.controller.get_control_value(self.controls[control_name])

    def get_format(self) -> None:
        try:
            curr_format = self.controller.get_format()
            self.valid_frame_rates = {
                round(1 / float(i)): i
                for i in self.controller.get_available_frame_intervals(*curr_format)
            }

            self.frame_rate = round(1 / float(self.controller.get_frame_interval()))

            self.color_format = curr_format[0].description
            self.resolution: tuple[int, int] = (curr_format[1].width, curr_format[1].height)
            
        except FileNotFoundError:
            CameraInfo.logger.fatal(f"Camera {self.identifier} disconnected. Cannot read information.")


    def export_configs(self) -> dict[str : int | str | float | bool]:
        self.get_format()

        configs = {}

        for property, ctrl in self.controls.items():
            if isinstance(ctrl, Menu):
                configs[property] = self.get(property).name
            else:
                configs[property] = self.get(property)

        configs["resolution"] = self.resolution
        configs["color_format"] = self.color_format
        configs["frame_rate"] = self.frame_rate
        configs["mode"] = self.mode.value

        return configs

    def export_config_options(self):
        configs = {}

        for property, ctrl in self.controls.items():
            if isinstance(ctrl, Menu):
                configs[property + "_MENU"] = list(map(lambda c: c.name, ctrl.items))
            else:
                configs[property + "_RANGE"] = [ctrl.minimum, ctrl.maximum, ctrl.step]

        configs["resolution" + "_MENU"] = self.valid_formats[self.color_format]
        configs["color_format" + "_MENU"] = list(self.valid_color_formats)
        configs["frame_rate" + "_MENU"] = list(
            map(lambda f: round(1 / float(f)), (self.valid_frame_rates.values()))
        )

        return configs
