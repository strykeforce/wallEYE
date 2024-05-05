import cv2
from camera.boot_up import *
from calibration.calibration import Calibration
import re
import os
from sys import platform
import logging
from camera.camera_info import CameraInfo
from pathlib import Path
from camera.v4l_cmd_line import getFormats, getSettings, setBrightness, setExposure
from directory import V4L_PATH, fullCamPath, cleanIdentifier, calibrationPathByCam


# Maintains camera info provided by cv2
class Cameras:
    logger = logging.getLogger(__name__)

    def __init__(self):
        # Cameras identified by their path (or whatever unique identifier is available)
        self.info = {}

        if platform == "linux" or platform == "linux2":
            Cameras.logger.info("Platform is linux")

            # Automatically detect cameras
            try:
                cameraPaths = os.listdir(V4L_PATH)
            except FileNotFoundError:
                cameraPaths = []
                Cameras.logger.error("No cameras detected!!")

            # Try all cameras found by the PI
            for identifier in cameraPaths:
                if (
                    Path("../../../deadeye").is_dir()
                    and identifier == "platform-xhci-hcd.9.auto-usb-0:1:1.0-video-index0"
                ):
                    continue

                path = fullCamPath(identifier)

                # Open camera and check if it is opened
                cam = cv2.VideoCapture(path, cv2.CAP_V4L2)

                if cam.isOpened():
                    Cameras.logger.info(f"Camera found: {identifier}")

                    # Get supported resolutions using v4l2-ctl and a little regex
                    supportedResolutions, formats = getFormats(identifier)
                    exposureRange, brightnessRange = getSettings(identifier)

                    Cameras.logger.info(
                        f"Supported resolutions: {supportedResolutions}"
                    )
                    Cameras.logger.info(f"Supported formats: {formats}")
                    Cameras.logger.info(
                        f"Supported exposures (min, max, step): {exposureRange}"
                    )
                    Cameras.logger.info(
                        f"Supported brightnesses (min, max, step): {brightnessRange}"
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

                    # Initialize CameraInfo object
                    self.info[identifier] = CameraInfo(cam, identifier, supportedResolutions)
                    self.info[identifier].resolution = self.getResolutions()[identifier]
                    self.info[identifier].exposureRange = exposureRange
                    self.info[identifier].brightnessRange = brightnessRange
                    self.info[identifier].validFormats = formats

                    # Attempt to import config from file
                    self.importConfig(identifier)

                    # Save configs
                    writeConfig(
                        identifier,
                        self.getResolutions()[identifier],
                        self.getBrightnesss()[identifier],
                        self.getExposures()[identifier],
                    )

                else:
                    Cameras.logger.warning(f"Failed to open camera: {identifier}")

        else:
            Cameras.logger.error("Unsupported platform!")

    def setCalibration(self, identifier, K, D):
        self.info[identifier].K = K
        self.info[identifier].D = D

        Cameras.logger.info(f"Calibration set for {identifier}, using {K}\n{D}")

    # Return a list of camera matrixs
    def listK(self):
        return [i.K for i in self.info.values()]

    # Return a list of camera distortion coefficients
    def listD(self):
        return [i.D for i in self.info.values()]

    # Grab frames from each camera
    def getFrames(self):
        frames = {}
        for identifier, camInfo in self.info.items():
            ret, img = camInfo.cam.read()

            if not ret:
                Cameras.logger.error(f"Failed to capture image: {identifier}")

            frames[identifier] = img
        return frames

    # Grab frames from each camera specifically for processing
    def getFramesForProcessing(self):
        frames = {}
        connections = {}
        for identifier, camInfo in self.info.items():
            ret, img = camInfo.cam.read()
            frames[identifier] = img
            connections[identifier] = ret
        return (connections, frames)

    # Sets resolution, video format, and FPS
    def setResolution(self, identifier, resolution):
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
                *("YUYV" if "YUYV" in self.info[identifier].validFormats else "GREY")
            ),
        )
        # self.info[identifier].cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
        self.info[identifier].cam.set(cv2.CAP_PROP_FPS, 5)  # Lower can be better
        resolution = tuple(resolution)

        # Test if resolution got set
        if self.getResolutions()[identifier] != resolution:
            Cameras.logger.error(
                f"Failed to set resolution to {resolution} for {identifier}, using {self.getResolutions()[identifier]}"
            )
            return False

        # Write a new config file with the new resolution
        self.info[identifier].resolution = resolution
        self.importCalibration(identifier)

        writeConfig(
            identifier,
            resolution,
            self.getBrightnesss()[identifier],
            self.getExposures()[identifier],
        )

        Cameras.logger.info(f"Resolution set to {resolution} for {identifier}")
        return True

    def setBrightness(self, identifier, brightness):
        if brightness is None:
            Cameras.logger.info("Brightness not set")
            return False

        # Set brightness through command line
        returned = setBrightness(identifier, brightness)

        # Check if it set, if so write it to a file
        if returned != 0:
            Cameras.logger.warning(
                f"Brightness not set: {brightness} not accepted on camera {identifier}"
            )
            return False
        else:
            Cameras.logger.info(f"Brightness set to {brightness}")
            writeConfig(
                identifier,
                self.getResolutions()[identifier],
                brightness,
                self.getExposures()[identifier],
            )
            return True

    def setExposure(self, identifier, exposure):
        if exposure is None:
            Cameras.logger.info("Exposure not set")
            return False

        # Set exposure with a command
        returned = setExposure(identifier, exposure)

        # Check if it set, if so write it to a file
        if returned != 0:
            Cameras.logger.warning(
                f"Exposure not set: {exposure} not accepted on camera {identifier}"
            )
            return False
        else:
            Cameras.logger.info(f"Exposure set to {exposure}")

            writeConfig(
                identifier,
                self.getResolutions()[identifier],
                self.getBrightnesss()[identifier],
                exposure,
            )
            return True

    # Return a dictionary of all camera exposures
    def getExposures(self):
        return {
            identifier: camInfo.cam.get(cv2.CAP_PROP_EXPOSURE)
            for identifier, camInfo in self.info.items()
        }

    # Return a dictionary of all camera brightnesss
    def getBrightnesss(self):
        return {
            identifier: camInfo.cam.get(cv2.CAP_PROP_BRIGHTNESS)
            for identifier, camInfo in self.info.items()
        }

    # Return a dictionary of all camera resolutions
    def getResolutions(self):
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
    def importCalibration(self, identifier):
        resolution = tuple(self.info[identifier].resolution)

        # Look for the calibration file
        try:
            calib = Calibration.parseCalibration(
                calibrationPathByCam(identifier, resolution)
            )

            # grab the camera matrix and distortion coefficent and set it
            self.setCalibration(identifier, calib["K"], calib["dist"])
            self.info[identifier].calibrationPath = calibrationPathByCam(
                identifier, resolution
            )
            return True
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            self.info[identifier].calibrationPath = None
            Cameras.logger.error(
                f"Calibration not found for camera {identifier} at resolution {resolution}"
            )
            return False

    def importConfig(self, identifier):
        # Attempt to import config from file
        Cameras.logger.info(f"Attempting to import config for {identifier}")
        config = None

        try:
            # Parse config from config file
            config = parseConfig(identifier)
            Cameras.logger.info(f"Config found!")

        except (FileNotFoundError, json.decoder.JSONDecodeError):
            Cameras.logger.warning(f"Config not found for camera {identifier}")

        if config is not None:
            # Config was found, set config data
            if not self.setResolution(
                identifier, config["Resolution"]
            ):  # Calls self.importCalibration iff resolution was set
                self.importCalibration(identifier)
            self.setBrightness(identifier, config["Brightness"])
            self.setExposure(identifier, config["Exposure"])

        else:
            self.importCalibration(identifier)
            Cameras.logger.warning(f"Camera config not found for camera {identifier}")

        return config
