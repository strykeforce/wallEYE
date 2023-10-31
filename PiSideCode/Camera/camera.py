import cv2
from Camera.BootUp import *
from Calibration.calibration import Calibration
import subprocess
import re
import os
from sys import platform
import logging
from Camera.CameraInfo import CameraInfo


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
                cameraPaths = os.listdir(r"/dev/v4l/by-path")
            except FileNotFoundError:
                cameraPaths = []
                Cameras.logger.error("No cameras detected!!")

            # Try all cameras found by the PI
            for camPath in cameraPaths:
                path = f"/dev/v4l/by-path/{camPath}"

                # Open camera and check if it is opened
                cam = cv2.VideoCapture(path, cv2.CAP_V4L2)

                if cam.isOpened():
                    Cameras.logger.info(f"Camera found: {camPath}")

                    # Get supported resolutions using v4l2-ctl and a little regex
                    supportedResolutions = sorted( # Sort values
                        list(
                            set( # Unique values
                                map(
                                    lambda x: (
                                        int(x.split("x")[0]),
                                        int(x.split("x")[1]),
                                    ),
                                    re.findall(
                                        "[0-9]+x[0-9]+",
                                        subprocess.run(
                                            [
                                                "v4l2-ctl",
                                                "-d",
                                                path,
                                                "--list-formats-ext",
                                            ],
                                            capture_output=True,
                                        ).stdout.decode("utf-8"),
                                    ),
                                )
                            )
                        )
                    )

                    Cameras.logger.info(
                        f"Supported resolutions: {supportedResolutions}"
                    )

                    # Disable buffer so we always pull the latest image
                    cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                    # Try to disable auto exposure
                    if cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1):
                        Cameras.logger.info(f"Auto exposure disabled for {camPath}")
                    else:
                        Cameras.logger.warning(
                            f"Failed to disable auto exposure for {camPath}"
                        )

                    # Initialize CameraInfo object
                    self.info[camPath] = CameraInfo(cam, camPath, supportedResolutions)
                    self.info[camPath].resolution = self.getResolutions()[camPath]

                    # Attempt to import config from file
                    self.importConfig(camPath)

                    # Save configs
                    writeConfig(
                        self.cleanIdentifier(camPath),
                        self.getResolutions()[camPath],
                        self.getGains()[camPath],
                        self.getExposures()[camPath],
                    )

        else:
            Cameras.logger.error("Unknown platform!")
    
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
            _, img = camInfo.cam.read()
            frames[identifier] = img
        return frames

    # Sets resolution, video format, and FPS
    def setResolution(self, identifier, resolution):
        if resolution is None:
            Cameras.logger.info("Resolution not set")
            return False
        # set resolution, fps, and video format
        # os.system(f"v4l2-ctl -d /dev/v4l/by-path/{identifier} --set-fmt-video=width={resolution[0]},height={resolution[1]}")
        self.info[identifier].cam.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        self.info[identifier].cam.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.info[identifier].cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.info[identifier].cam.set(cv2.CAP_PROP_FPS, 30)
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
            self.cleanIdentifier(identifier),
            resolution,
            self.getGains()[identifier],
            self.getExposures()[identifier],
        )

        Cameras.logger.info(f"Resolution set to {resolution} for {identifier}")
        return True

    def setGain(self, identifier, gain):
        if gain is None:
            Cameras.logger.info("Gain not set")
            return False

        # Set gain through command line
        os.system(f"v4l2-ctl -d /dev/v4l/by-path/{identifier} --set-ctrl gain={gain}")

        # Check if it set, if so write it to a file
        if self.info[identifier].cam.get(cv2.CAP_PROP_GAIN) != gain:
            Cameras.logger.warning(f"Gain not set: {gain} not accepted")
            return False
        else:
            Cameras.logger.info(f"Gain set to {gain}")
            writeConfig(
                self.cleanIdentifier(identifier),
                self.getResolutions()[identifier],
                gain,
                self.getExposures()[identifier],
            )
            return True

    def setExposure(self, identifier, exposure):
        if exposure is None:
            Cameras.logger.info("Exposure not set")
            return False

        # Set exposure with a command
        os.system(
            f"v4l2-ctl -d /dev/v4l/by-path/{identifier} --set-ctrl exposure_auto=1 --set-ctrl exposure_absolute={exposure}"
        )

        # Check if it set, if so write it to a file
        if self.info[identifier].cam.get(cv2.CAP_PROP_EXPOSURE) != exposure:
            Cameras.logger.warning(f"Exposure not set: {exposure} not accepted")
            return False
        else:
            Cameras.logger.info(f"Exposure set to {exposure}")

            writeConfig(
                self.cleanIdentifier(identifier),
                self.getResolutions()[identifier],
                self.getGains()[identifier],
                exposure,
            )
            return True

    # Return a dictionary of all camera exposures
    def getExposures(self):
        exposure = {}
        for identifier, camInfo in self.info.items():
            exposure[identifier] = camInfo.cam.get(cv2.CAP_PROP_EXPOSURE)
        return exposure

    # Return a dictionary of all camera gains
    def getGains(self):
        gain = {}
        for identifier, camInfo in self.info.items():
            gain[identifier] = camInfo.cam.get(cv2.CAP_PROP_GAIN)
        return gain

    # Return a dictionary of all camera resolutions
    def getResolutions(self):
        resolution = {}
        for identifier, camInfo in self.info.items():
            resolution[identifier] = (
                int(camInfo.cam.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(camInfo.cam.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            )

        return resolution

    # Find a calibration for the camera
    def importCalibration(self, identifier):
        resolution = tuple(self.info[identifier].resolution)

        # Look for the calibration file
        try:
            calib = Calibration.parseCalibration(
                Calibration.calibrationPathByCam(identifier, resolution)
            )

            # grab the camera matrix and distortion coefficent and set it
            self.setCalibration(identifier, calib["K"], calib["dist"])
            self.info[identifier].calibrationPath = Calibration.calibrationPathByCam(
                identifier, resolution
            )
            return True
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            self.info[identifier].calibrationPath = None
            Cameras.logger.error(
                f"Calibration not found for camera {identifier} at resolution {resolution}"
            )
            return False
    
    def importConfig(self, camPath):
        # Attempt to import config from file
        Cameras.logger.info(f"Attempting to import config for {camPath}")
        cleaned = self.cleanIdentifier(camPath)
        config = None

        try:
            # Parse config from config file
            config = parseConfig(cleaned)
            Cameras.logger.info(f"Config found!")

        except (FileNotFoundError, json.decoder.JSONDecodeError):
            Cameras.logger.warning(f"Config not found for camera {camPath}")

        if config is not None:
            # Config was found, set config data
            if not self.setResolution(
                camPath, config["Resolution"]
            ):  # Calls self.importCalibration iff resolution was set
                self.importCalibration(camPath)
            self.setGain(camPath, config["Gain"])
            self.setExposure(camPath, config["Exposure"])

        else:
            self.importCalibration(camPath)
            Cameras.logger.warning(
                f"Camera config not found for camera {camPath}"
            )
        
        return config

    @staticmethod
    def cleanIdentifier(identifier):
        return identifier.replace(":", "-").replace(".", "-")
