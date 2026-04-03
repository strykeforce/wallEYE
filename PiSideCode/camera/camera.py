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
            for identifier in sorted(camera_paths):
                if is_disabled(identifier):
                    Cameras.logger.info(f"Skipping {identifier} - DISABLED")
                    continue

                if "-usbv2-" in identifier or "-usbv3-" in identifier:
                    Cameras.logger.info(f"Skipping {identifier} - DUPLICATE")
                    continue        

                path = full_cam_path(identifier)

                for attempt in range(3):
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
                        eventlet.sleep(0.1)

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
                        break

                    else:
                        cam.release()

                        Cameras.logger.warning(f"Failed to open camera (attempt {attempt + 1}): for {identifier}")
                        eventlet.sleep(0.2)

            Thread(target=self._capture_thread, daemon=True).start()

        else:
            Cameras.logger.error("Unsupported platform!")

    def reopen(self, identifier):
        cam_info = self.info[identifier]
        path = full_cam_path(identifier)
        
        # Ensure the old handle is closed first
        if cam_info.cam is not None:
            cam_info.cam.release()

        for attempt in range(3):
            cam = cv2.VideoCapture(path, cv2.CAP_V4L2)
            
            if cam.isOpened():
                Cameras.logger.info(f"Camera {identifier} RECOVERED on attempt {attempt + 1}")
                
                # Re-assign the new camera object to the existing info
                cam_info.cam = cam
                
                # Import config from file
                self.import_config(identifier)
                
                # Disable buffer so we always pull the latest image
                cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                # Try to disable auto exposure
                cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
                return True
            else:
                cam.release()
                Cameras.logger.warning(f"Recovery attempt {attempt + 1} failed for {identifier}")
                time.sleep(0.2) # Wait for USB bus to settle

        return False
    
    def _capture_thread(self):
        while True:
            '''
            # TODO: determine if this is useful
            # High-speed grab loop to discard stale frames
            for identifier in self.info.keys():
                cam_info = self.info[identifier]
                cam_info.cam.grab() 
            '''
           
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

        # If this camera is currently being re-opened, don't try to read it
        if cam_info.is_recovering:
            # Populate data and exit
            self.frames[self.new_data_index][identifier] = None
            self.connections[self.new_data_index][identifier] = False
            self.timestamp[self.new_data_index][identifier] = 0.0
            self.cam_read_delay[self.new_data_index][identifier] = 0.0
            return

        ret, img = False, None
        before = time.perf_counter()

        try:
            ret, img = cam_info.cam.read()

            if not ret:
                # Read fails, shift to recovery mode and start the recovery background thread
                cam_info.is_recovering = True
                Cameras.logger.warning(f"Read failed for {identifier}. Starting background recovery...")
                Thread(target=self._background_reopen, args=(identifier,), daemon=True).start()

                # Populate data and exit
                self.frames[self.new_data_index][identifier] = None
                self.connections[self.new_data_index][identifier] = False
                self.timestamp[self.new_data_index][identifier] = 0.0
                self.cam_read_delay[self.new_data_index][identifier] = 0.0
                return
            else:
                # Grab timestamps first
                stream_time_ms = cam_info.cam.get(cv2.CAP_PROP_POS_MSEC)
                after = time.perf_counter()

                # Calculate glass time
                exp_time_ms = cam_info.get("Exposure Time, Absolute") * 0.1
                usb_transfer_time_ms = 16.7 #TODO: Get this from somewhere?
                glass_time_ms = stream_time_ms - usb_transfer_time_ms - 0.5*exp_time_ms

                # Populate normal data
                self.frames[self.new_data_index][identifier] = img
                self.connections[self.new_data_index][identifier] = ret
                self.timestamp[self.new_data_index][identifier] = glass_time_ms
                self.cam_read_delay[self.new_data_index][identifier] = round(after - before, 3)

        except Exception as e:
            Cameras.logger.error(f"Failed to read frame", exc_info=e)

    def _background_reopen(self, identifier):
        # Background recovery thread.
        try:
            time.sleep(0.2)
            # This calls your existing reopen() which handles release, open, and import_config
            success = self.reopen(identifier)
            if success:
                Cameras.logger.info(f"Background recovery successful for {identifier}")
            else:
                Cameras.logger.error(f"Background recovery failed for {identifier}")
        finally:
            # Always clear the flag so _read_frame can try again next loop
            self.info[identifier].is_recovering = False

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

        else:
            self.import_calibration(identifier)
            Cameras.logger.warning(f"Camera config not found for camera {identifier}")

        return config

    def write_configs(self, identifier):
        with open(cam_config_path(identifier), "w") as file:
            json.dump(self.info[identifier].export_configs(), file)
