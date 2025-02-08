import cv2
from camera.camera_config import write_config, parse_config, is_disabled
from camera.camera_info import Modes
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
from concurrent.futures import ThreadPoolExecutor
from threading import Thread, Lock
import eventlet
import sys


# np.set_printoptions(threshold=sys.maxsize)
class Cameras:
    logger = logging.getLogger(__name__)

    def __init__(self):
        # Cameras identified by their path (or whatever unique identifier is
        # available)
        self.info: dict[str, CameraInfo] = {}

        self.frames: list[dict[str, np.ndarray]] = [{}, {}]
        self.connections: list[dict[str, bool]] = [{}, {}]
        self.timestamp: list[dict[str, float]] = [{}, {}]
        self.cam_read_delay: list[dict[str, float]] = [{}, {}]

        self.executor: ThreadPoolExecutor = ThreadPoolExecutor()
        self.new_data_lock: Lock = Lock()
        self.new_data_index: int = 0
        self.written_index: int = 1
        self.fresh_data: list[bool] = [False, False]

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
                if is_disabled(identifier):
                    Cameras.logger.info(f"Skipping {identifier} - DISABLED")
                    continue

                if "-usbv2-" in identifier:
                    Cameras.logger.info(f"Skipping {identifier} - DUPLICATE")
                    continue

                path = full_cam_path(identifier)

                # Open camera and check if it is opened
                cam = cv2.VideoCapture(path, cv2.CAP_V4L2)

                # time.sleep(10)

                if cam.isOpened():
                    Cameras.logger.info(f"Camera found: {identifier}")

                    # Initialize CameraInfo object
                    self.info[identifier] = CameraInfo(cam, identifier)

                    # Attempt to import config from file
                    self.import_config(identifier)

                    # Save configs
                    eventlet.sleep(5)

                    # write_config(identifier, self.info[identifier])

                    # Disable buffer so we always pull the latest image
                    cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                    # Try to disable auto exposure
                    if cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1):
                        Cameras.logger.info(f"Auto exposure disabled for {identifier}")
                    else:
                        Cameras.logger.warning(
                            f"Failed to disable auto exposure for {identifier}"
                        )

                else:
                    Cameras.logger.error(f"Failed to open camera: {identifier}")

            Thread(target=self._capture_thread, daemon=True).start()

        else:
            Cameras.logger.error("Unsupported platform!")

    def _capture_thread(self):
        while True:
            list(self.executor.map(self._read_frame, self.info.keys()))

            if self.new_data_lock.locked():
                self.new_data_lock.release()

            self.fresh_data[self.new_data_index] = True

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

    def get_frame(self, identifier: str) -> list[np.ndarray]:
        self.want_new_frames()
        self.fresh_data[self.written_index] = False

        return self.frames[self.written_index][identifier]

    # Grab frames from each camera specifically for processing
    def get_frames_for_processing(
        self,
    ) -> tuple[
        dict[str, bool], dict[str, np.ndarray], dict[str, float], dict[str, float]
    ]:
        self.want_new_frames()
        self.fresh_data[self.written_index] = False

        return (
            self.connections[self.written_index],
            self.frames[self.written_index],
            self.timestamp[self.written_index],
            self.cam_read_delay[self.written_index],
        )

    def want_new_frames(self):
        # New data at our read index
        if self.fresh_data[self.written_index]:
            return

        # Both slots have old data
        if not self.fresh_data[self.new_data_index]:
            self.new_data_lock.acquire()

        # Old data at current index but new in other
        self.written_index = self.new_data_index
        self.new_data_index = (self.new_data_index + 1) % 2

    def _read_frame(self, identifier):
        # eventlet.sleep(0.1) # FIXME cam returns None sometimes, delay could help???
        # [ WARN:1@259.552] global cap_v4l.cpp:1048 tryIoctl VIDEOIO(V4L2 select() timeout.
        cam_info = self.info[identifier]
        ret, img = False, None
        before = time.perf_counter()

        try:
            ret, img = cam_info.cam.read()
        except Exception as e:
            Cameras.logger.error(f"Failed to read frame", exc_info=e)

        self.cam_read_delay[self.new_data_index][identifier] = round(
            time.perf_counter() - before, 3
        )
        self.frames[self.new_data_index][identifier] = img
        self.connections[self.new_data_index][identifier] = ret
        self.timestamp[self.new_data_index][identifier] = cam_info.cam.get(
            cv2.CAP_PROP_POS_MSEC
        )

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
                elif property == "mode":
                    camera_info.mode = Modes(value)
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
