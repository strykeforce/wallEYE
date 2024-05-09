import cv2
from camera.boot_up import write_config, parse_config
from calibration.calibration import Calibration
import os
import time
from sys import platform
import logging
from camera.camera_info import CameraInfo, EXPOSURE, BRIGHTNESS
from pathlib import Path
from directory import V4L_PATH, full_cam_path, calibration_path_by_cam
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

                    # Get supported resolutions using v4l2-ctl and a little
                    # regex
                    # OLD (from import v4l_cmd_line import getFormats, getSettings)
                    # supportedResolutions, formats = getFormats(identifier)
                    # exposureRange, brightnessRange = getSettings(identifier)

                    # Initialize CameraInfo object
                    self.info[identifier] = CameraInfo(cam, identifier)

                    Cameras.logger.info(
                        f"Supported resolutions: {self.info[identifier].get_supported_resolutions()}"
                    )
                    Cameras.logger.info(
                        f"Supported formats: {list(self.info[identifier].valid_formats.keys())}"
                    )
                    Cameras.logger.info(
                        f"Supported exposures (min, max, step): {self.info[identifier].exposure_range}"
                    )
                    Cameras.logger.info(
                        f"Supported brightnesses (min, max, step): {self.info[identifier].brightness_range}"
                    )

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
                    write_config(
                        identifier,
                        self.get_resolutions()[identifier],
                        self.get_brightnesss()[identifier],
                        self.get_exposures()[identifier],
                    )

                else:
                    Cameras.logger.warning(f"Failed to open camera: {identifier}")

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
        delay = {}
        for identifier, camInfo in self.info.items():
            ret, img = camInfo.cam.read()

            # if not ret:
            #     Cameras.logger.error(f"Failed to capture image: {identifier}")

            frames[identifier] = img
            connections[identifier] = ret
            delay[identifier] = time.clock_gettime_ns(
                time.CLOCK_MONOTONIC
            ) / 1000000 - camInfo.cam.get(
                cv2.CAP_PROP_POS_MSEC
            )  # Expect -28 to -32 on laptop testing TODO CHECK THIS

        return (connections, frames, delay)

    # Sets resolution, video format, and FPS
    def set_resolution(self, identifier: str, resolution: tuple[int, int]) -> bool:
        if resolution is None:
            Cameras.logger.info("Resolution not set")
            return False
        # set resolution, fps, and video format
        # os.system(f"v4l2-ctl -d /dev/v4l/by-path/{identifier} --set-fmt-video=width={resolution[0]},height={resolution[1]}")
        self.info[identifier].cam.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        self.info[identifier].cam.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.info[identifier].cam.set(
            cv2.CAP_PROP_FOURCC,
            cv2.VideoWriter_fourcc(
                *(
                    "YUYV"
                    if "YUYV" in "".join(self.info[identifier].valid_formats)
                    else "GREY"
                )
            ),
        )
        # self.info[identifier].cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
        self.info[identifier].cam.set(cv2.CAP_PROP_FPS, 5)  # Lower can be better
        resolution = tuple(resolution)

        # Test if resolution got set
        if self.get_resolutions()[identifier] != resolution:
            Cameras.logger.error(
                f"Failed to set resolution to {resolution} for {identifier}, using {self.get_resolutions()[identifier]}"
            )
            return False

        # Write a new config file with the new resolution
        self.info[identifier].resolution = resolution
        self.import_calibration(identifier)

        write_config(
            identifier,
            resolution,
            self.get_brightnesss()[identifier],
            self.get_exposures()[identifier],
        )

        Cameras.logger.info(f"Resolution set to {resolution} for {identifier}")
        return True

    def set_brightness(self, identifier: str, brightness: float) -> bool:
        if brightness is None:
            Cameras.logger.info("Brightness not set")
            return False

        success = self.info[identifier].set(BRIGHTNESS, brightness)

        if success:
            write_config(
                identifier,
                self.get_resolutions()[identifier],
                brightness,
                self.get_exposures()[identifier],
            )

        return success

        # Set brightness through command line
        # returned = setBrightness(identifier, brightness)

        # Check if it set, if so write it to a file
        # if returned != 0:
        #     Cameras.logger.warning(
        #         f"Brightness not set: {brightness} not accepted on camera {identifier}"
        #     )
        #     return False
        # else:
        #     Cameras.logger.info(f"Brightness set to {brightness}")
        #     writeConfig(
        #         identifier,
        #         self.getResolutions()[identifier],
        #         brightness,
        #         self.getExposures()[identifier],
        #     )
        #     return True

    def set_exposure(self, identifier: str, exposure: float) -> bool:
        if exposure is None:
            Cameras.logger.info("Exposure not set")
            return False

        success = self.info[identifier].set(EXPOSURE, exposure)

        if success:
            write_config(
                identifier,
                self.get_resolutions()[identifier],
                self.get_brightnesss()[identifier],
                exposure,
            )

        return success

        # Set exposure with a command
        # returned = setExposure(identifier, exposure)

        # Check if it set, if so write it to a file
        # if returned != 0:
        #     Cameras.logger.warning(
        #         f"Exposure not set: {exposure} not accepted on camera {identifier}"
        #     )
        #     return False
        # else:
        #     Cameras.logger.info(f"Exposure set to {exposure}")

        #     writeConfig(
        #         identifier,
        #         self.getResolutions()[identifier],
        #         self.getBrightnesss()[identifier],
        #         exposure,
        #     )
        #     return True

    # Return a dictionary of all camera exposures
    def get_exposures(self) -> dict[str, float]:
        return {
            identifier: camInfo.cam.get(cv2.CAP_PROP_EXPOSURE)
            for identifier, camInfo in self.info.items()
        }

    # Return a dictionary of all camera brightnesss
    def get_brightnesss(self) -> dict[str, float]:
        return {
            identifier: camInfo.cam.get(cv2.CAP_PROP_BRIGHTNESS)
            for identifier, camInfo in self.info.items()
        }

    # Return a dictionary of all camera resolutions
    def get_resolutions(self) -> dict[str, tuple[int, int]]:
        resolution = {}
        for identifier, camInfo in self.info.items():
            resolution[identifier] = (
                int(camInfo.cam.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(camInfo.cam.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            )

        return {
            identifier: (
                int(camInfo.cam.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(camInfo.cam.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            )
            for identifier, camInfo in self.info.items()
        }

    # Find a calibration for the camera
    def import_calibration(self, identifier: str) -> bool:
        resolution = tuple(self.info[identifier].resolution)

        # Look for the calibration file
        try:
            calib = Calibration.parse_calibration(
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

        try:
            # Parse config from config file
            config = parse_config(identifier)
            Cameras.logger.info(f"Config found!")

        except (FileNotFoundError, json.decoder.JSONDecodeError):
            Cameras.logger.warning(f"Config not found for camera {identifier}")

        if config is not None:
            # Config was found, set config data
            if not self.set_resolution(
                identifier, config["Resolution"]
            ):  # Calls self.importCalibration iff resolution was set
                self.import_calibration(identifier)
            self.set_brightness(identifier, config["Brightness"])
            self.set_exposure(identifier, config["Exposure"])

        else:
            self.import_calibration(identifier)
            Cameras.logger.warning(f"Camera config not found for camera {identifier}")

        return config
