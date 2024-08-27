import cv2
from camera.camera_config import write_config, parse_config
from calibration.calibration import Calibrator
import os
import time
from sys import platform
import logging
from camera.camera_info import CameraInfo
from pathlib import Path
from directory import V4L_PATH, full_cam_path, calibration_path_by_cam, cam_config_path
import json
import numpy as np


class Cameras:
    logger = logging.getLogger(__name__)

    def __init__(self):
        # Cameras identified by their path (or whatever unique identifier is
        # available)
        self.info: dict[str, CameraInfo] = {}

        if platform == "linux" or platform == "linux2":
            Cameras.logger.info("Platform is linux")

            # Automatically detect cameras
            try:
                camera_paths = os.listdir(V4L_PATH)
            except FileNotFoundError:
                camera_paths = []
                Cameras.logger.error("No cameras detected!!")

            # Try all cameras found by the PI
            for identifier in camera_paths:
                if (
                    Path("../../../deadeye").is_dir()
                    and identifier
                    == "platform-xhci-hcd.9.auto-usb-0:1:1.0-video-index0"
                ):
                    continue

                path = full_cam_path(identifier)

                # Open camera and check if it is opened
                cam = cv2.VideoCapture(path, cv2.CAP_V4L2)

                if cam.isOpened():
                    Cameras.logger.info(f"Camera found: {identifier}")

                    # Initialize CameraInfo object
                    self.info[identifier] = CameraInfo(cam, identifier)

                    # Disable buffer so we always pull the latest image
                    cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                    # Try to disable auto exposure
                    if cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1):
                        Cameras.logger.info(f"Auto exposure disabled for {identifier}")
                    else:
                        Cameras.logger.warning(
                            f"Failed to disable auto exposure for {identifier}"
                        )

                    # Attempt to import config from file
                    self.import_config(identifier)

                    # Save configs
                    write_config(identifier, self.info[identifier])

                else:
                    Cameras.logger.error(f"Failed to open camera: {identifier}")

        else:
            Cameras.logger.error("Unsupported platform!")

    def set_calibration(self, identifier: str, K: np.ndarray, D: np.ndarray):
        self.info[identifier].K = K
        self.info[identifier].D = D

        Cameras.logger.info(f"Calibration set for {identifier}, using {K}\n{D}")

    # Return a list of camera matrixs
    def list_k(self) -> list[np.ndarray]:
        return [i.K for i in self.info.values()]

    # Return a list of camera distortion coefficients
    def list_d(self) -> list[np.ndarray]:
        return [i.D for i in self.info.values()]

    # Grab frames from each camera specifically for processing
    def get_frames_for_processing(
        self,
    ) -> tuple[dict[str, bool], dict[str, np.ndarray], dict[str, float]]:
        frames = {}
        connections = {}
        timestamp = {}
        cam_read_time = {}
        for identifier, camInfo in self.info.items():
            before = time.perf_counter()
            ret, img = camInfo.cam.read()

            cam_read_time[identifier] = round(time.perf_counter() - before, 3)
            frames[identifier] = img
            connections[identifier] = ret
            timestamp[identifier] = camInfo.cam.get(cv2.CAP_PROP_POS_MSEC)

        return (connections, frames, timestamp, cam_read_time)

    # Find a calibration for the camera
    def import_calibration(self, identifier: str) -> bool:
        resolution = tuple(self.info[identifier].resolution)

        # Look for the calibration file
        try:
            calib = Calibrator.parse_calibration(
                calibration_path_by_cam(identifier, resolution)
            )

            # grab the camera matrix and distortion coefficent and set it
            self.set_calibration(identifier, calib["K"], calib["dist"])
            self.info[identifier].calibration_path = calibration_path_by_cam(
                identifier, resolution
            )
            return True
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            self.info[identifier].calibration_path = None
            Cameras.logger.error(
                f"Calibration not found for camera {identifier} at resolution {resolution}"
            )
            return False

    def import_config(
        self, identifier: str
    ) -> dict[str, float | str | list[int] | None] | None:
        # Attempt to import config from file
        Cameras.logger.info(f"Attempting to import config for {identifier}")
        config = None
        camera_info = self.info[identifier]

        try:
            # Parse config from config file
            config = parse_config(identifier, camera_info)
            Cameras.logger.info(f"Config found!")

        except (FileNotFoundError, json.decoder.JSONDecodeError):
            Cameras.logger.warning(f"Config not found for camera {identifier}")

        if config is not None:
            # Config was found, set config data

            for property, value in config.items():
                if property == "resolution":
                    camera_info.set_resolution(value)
                elif property == "color_format":
                    camera_info.set_color_format(value)
                elif property == "frame_rate":
                    camera_info.set_frame_rate(value)
                else:
                    self.info[identifier].set(property, value)
            self.import_calibration(identifier)

            self.write_configs(identifier)

        else:
            self.import_calibration(identifier)
            Cameras.logger.warning(f"Camera config not found for camera {identifier}")

        return config

    def write_configs(self, identifier):
        with open(cam_config_path(identifier), "w") as file:
            json.dump(self.info[identifier].export_configs(), file)
