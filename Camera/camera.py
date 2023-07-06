import cv2
from Camera.BootUp import *
from Calibration.calibration import Calibration
import subprocess
import re
import os
from sys import platform
import logging


# Holds information about the camera including the object itself
# Not any existing VideoCapture properties like exposure
class CameraInfo:
    def __init__(self, cam, identifier, supportedResolutions, K=None, D=None):
        self.cam = cam
        self.identifier = identifier
        self.supportedResolutions = supportedResolutions

        # Calibration
        self.K = K
        self.D = D

        self.calibrationPath = None


# Maintains camera info provided by cv2
class Cameras:
    logger = logging.getLogger(__name__)

    def __init__(self):
        # Cameras identified by their path (or whatever unique identifier is available)
        self.info = {}

        if platform == "linux" or platform == "linux2":
            Cameras.logger.info("Platform is linux")

            # Automatically detect cameras
            cameraPaths = os.listdir(r"/dev/v4l/by-path")

            for camPath in cameraPaths:
                path = f"/dev/v4l/by-path/{camPath}"
                cam = cv2.VideoCapture(path, cv2.CAP_V4L2)

                if cam.isOpened():
                    Cameras.logger.info(f"Camera found: {camPath}")

                    supportedResolutions = sorted(
                        list(
                            set(
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

                    cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    if cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1):
                        Cameras.logger.info(f"Auto exposure disabled for {camPath}")
                    else:
                        Cameras.logger.warning(
                            f"Failed to disable auto exposure for {camPath}"
                        )

                    self.info[camPath] = CameraInfo(cam, camPath, supportedResolutions)

                    cleaned = Calibration.calibrationPathByCam(camPath)
                    try:
                        config = parseConfig(cleaned)
                        calib = Calibration.parseCalibration(cleaned)

                        self.setCalibration(camPath, calib["K", calib["dist"]])

                        self.info[camPath].calibrationPath = cleaned

                        Cameras.logger.info(
                            f"Calibration found! Using\n{calib['K']}\n{calib['dist']}"
                        )
                    except FileNotFoundError:
                        Cameras.logger.warning(
                            f"Calibration not found for camera {camPath}"
                        )

                    if config["Resolution"] is not None:
                        self.setResolution(camPath, config["Resolution"])
                        self.setGain(camPath, config["Gain"])
                        self.setExposure(camPath, config["Exposure"])
                    else:
                        Cameras.logger.warning(
                            f"Camera config not found for camera {camPath}"
                        )

                    # Save configs
                    writeConfig(
                        self.cleanIdentifier(camPath),
                        self.getResolutions()[camPath],
                        self.getGains()[camPath],
                        self.getExposures()[camPath],
                    )

        elif platform == "win32":
            # Debugging only
            # One camera only
            Cameras.logger.warning("Platform is windows")

            cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)

            if cam.isOpened():
                cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                supportedResolutions = [(640, 480), (1280, 720)]
                placeholderPath = "Windows0"

                if cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, -7):
                    Cameras.logger.info(f"Auto exposure disabled for {placeholderPath}")
                else:
                    Cameras.logger.warning(
                        f"Failed to disable auto exposure for {placeholderPath}"
                    )

                self.info[placeholderPath] = CameraInfo(
                    cam, placeholderPath, supportedResolutions
                )

                try:
                    config = parseConfig(placeholderPath)
                    calib = Calibration.parseCalibration(
                        f"./Calibration/Cam_{placeholderPath}CalData.json"
                    )

                    self.setCalibration(placeholderPath, calib["K"], calib["dist"])

                    self.info[
                        placeholderPath
                    ].calibrationPath = (
                        f"./Calibration/Cam_{placeholderPath}CalData.json"
                    )

                    Cameras.logger.info(
                        f"Calibration found! Using\n{calib['K']}\n{calib['dist']}"
                    )
                except FileNotFoundError:
                    Cameras.logger.warning(
                        f"Calibration not found for camera {placeholderPath}"
                    )

                if config["Resolution"] is not None:
                    self.setResolution(placeholderPath, config["Resolution"])
                    self.setGain(placeholderPath, config["Gain"])
                    self.setExposure(placeholderPath, config["Exposure"])
                else:
                    Cameras.logger.warning(
                        f"Camera config not found for camera {camPath}"
                    )

                # Save configs
                writeConfig(
                    placeholderPath,
                    self.getResolutions()[placeholderPath],
                    self.getGains()[placeholderPath],
                    self.getExposures()[placeholderPath],
                )

        else:
            Cameras.logger.error("Unknown platform!")

    def setCalibration(self, identifier, K, D):
        self.info[identifier].K = K
        self.info[identifier].D = D

        Cameras.logger.info(f"Calibration set for {identifier}")

    def listK(self):
        return [i.K for i in self.info.values()]

    def listD(self):
        return [i.D for i in self.info.values()]

    # These functions call existing cv2 setters/getters
    def getFrames(self):
        frames = {}
        for identifier, camInfo in self.info.items():
            _, img = camInfo.cam.read()
            frames[identifier] = img
        return frames

    def setResolution(self, identifier, resolution):
        if resolution is None:
            Cameras.logger.info("Resolution not set")
            return
        self.info[identifier].cam.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.info[identifier].cam.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

        writeConfig(
            self.cleanIdentifier(identifier),
            resolution,
            self.getGains()[identifier],
            self.getExposures()[identifier],
        )

        Cameras.logger.info(f"Resolution set to {resolution} for {identifier}")

    def setGain(self, identifier, gain):
        if gain is None:
            Cameras.logger.info("Gain not set")
            return

        if self.info[identifier].cam.set(cv2.CAP_PROP_GAIN, gain):
            Cameras.logger.warning(f"Gain not set: {gain} not accepted")
        else:
            Cameras.logger.info(f"Gain set to {gain}")
            writeConfig(
                self.cleanIdentifier(identifier),
                self.getResolutions()[identifier],
                gain,
                self.getExposures()[identifier],
            )

    def setExposure(self, identifier, exposure):
        if exposure is None:
            Cameras.logger.info("Exposure not set")
            return

        if self.info[identifier].cam.set(cv2.CAP_PROP_EXPOSURE, exposure):
            Cameras.logger.warning(f"Exposure not set: {exposure} not accepted")
        else:
            Cameras.logger.info(f"Exposure set to {exposure}")

            writeConfig(
                self.cleanIdentifier(identifier),
                self.getResolutions()[identifier],
                self.getGains()[identifier],
                exposure,
            )

    def getExposures(self):
        exposure = {}
        for identifier, camInfo in self.info.items():
            exposure[identifier] = camInfo.cam.get(cv2.CAP_PROP_EXPOSURE)
        return exposure

    def getGains(self):
        gain = {}
        for identifier, camInfo in self.info.items():
            gain[identifier] = camInfo.cam.get(cv2.CAP_PROP_GAIN)
        return gain

    def getResolutions(self):
        resolution = {}
        for identifier, camInfo in self.info.items():
            resolution[identifier] = (
                int(camInfo.cam.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(camInfo.cam.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            )

        return resolution

    @staticmethod
    def cleanIdentifier(identifier):
        return identifier.replace(":", "-").replace(".", "-")
