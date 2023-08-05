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
    def __init__(
        self, cam, identifier, supportedResolutions, resolution=None, K=None, D=None
    ):
        self.cam = cam
        self.identifier = identifier
        self.resolution = resolution
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
            try:
                cameraPaths = os.listdir(r"/dev/v4l/by-path")
            except FileNotFoundError:
                cameraPaths = []
                Cameras.logger.error("No cameras detected!!")

            for camPath in cameraPaths:
                path = f"/dev/v4l/by-path/{camPath}"
                cam = cv2.VideoCapture(path, cv2.CAP_V4L2)

                if cam.isOpened():
                    Cameras.logger.info(f"Camera found: {camPath}")

                    supportedResolutions = list(
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
                    self.info[camPath].resolution = self.getResolutions()[camPath]

                    cleaned = self.cleanIdentifier(camPath)

                    config = None
                    try:
                        config = parseConfig(cleaned)

                        Cameras.logger.info(f"Config found!")
                    except (FileNotFoundError, json.decoder.JSONDecodeError):
                        Cameras.logger.warning(f"Config not found for camera {camPath}")

                    if config is not None:
                        self.setResolution(
                            camPath, config["Resolution"]
                        )  # Calls self.importCalibration
                        self.setGain(camPath, config["Gain"])
                        self.setExposure(camPath, config["Exposure"])
                    else:
                        self.importCalibration(camPath)
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

        else:
            Cameras.logger.error("Unknown platform!")

    def setCalibration(self, identifier, K, D):
        self.info[identifier].K = K
        self.info[identifier].D = D

        Cameras.logger.info(f"Calibration set for {identifier}, using {K}\n{D}")

    def listK(self):
        return [i.K for i in self.info.values()]

    def listD(self):
        return [i.D for i in self.info.values()]

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

        self.info[identifier].resolution = resolution
        self.importCalibration(identifier)

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

        os.system("v4l2-ctl -d /dev/v4l/by-path/{identifier} --set-ctrl exposure_auto=1 -c gain={gain}")

        if self.info[identifier].cam.get(cv2.CAP_PROP_GAIN) != gain:
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
        
        os.system("v4l2-ctl -d /dev/v4l/by-path/{identifier} --set-ctrl exposure_auto=1 -c exposure_absolute={exposure}")

        if self.info[identifier].cam.get(cv2.CAP_PROP_EXPOSURE) != exposure:
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

    def importCalibration(self, identifier):
        resolution = tuple(self.info[identifier].resolution)

        try:
            calib = Calibration.parseCalibration(
                Calibration.calibrationPathByCam(identifier, resolution)
            )

            self.setCalibration(identifier, calib["K"], calib["dist"])

            self.info[identifier].calibrationPath = Calibration.calibrationPathByCam(
                identifier, resolution
            )

            Cameras.logger.info(
                f"Calibration found! Using\n{calib['K']}\n{calib['dist']}"
            )
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            self.info[identifier].calibrationPath = None
            Cameras.logger.error(
                f"Calibration not found for camera {identifier} at resolution {resolution}"
            )

    @staticmethod
    def cleanIdentifier(identifier):
        return identifier.replace(":", "-").replace(".", "-")
