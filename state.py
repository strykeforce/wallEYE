from enum import Enum
from Publisher.NetworkTablePublisher import NetworkIO
import logging
import os

class States(Enum):
    IDLE = "IDLE"
    BEGIN_CALIBRATION = "BEGIN_CALIBRATION"
    CALIBRATION_CAPTURE = "CALIBRATION_CAPTURE"
    GENERATE_CALIBRATION = "GENERATE_CALIBRATION"
    PROCESSING = "PROCESSING"
    SHUTDOWN = "SHUTDOWN"


CALIBRATION_STATES = (
    States.BEGIN_CALIBRATION,
    States.CALIBRATION_CAPTURE,
    States.GENERATE_CALIBRATION,
)


class Config:
    logger = logging.getLogger(__name__)

    def __init__(self) -> None:
        self.teamNumber = 2767
        self.tableName = "Walleye"

        self.currentState = States.PROCESSING

        # Calibration
        self.cameraInCalibration = None
        self.boardDims = (7, 7)
        self.calDelay = 1
        self.calImgPaths = []
        self.reprojectionError = None

        # Cams
        self.cameras = None

        self.robotPublisher = None

        self.poses = {}

        self.ip = None

        try:
            self.ip = Config.getCurrentIP()
            Config.logger.info(f"IP is {self.ip}")
        except IndexError:
            Config.logger.error("Could not get current IP")

    def makePublisher(self, teamNumber, tableName):
        self.teamNumber = teamNumber
        self.tableName = tableName

        if self.robotPublisher is not None:
            self.robotPublisher.destroy()
            Config.logger.info("Existing publisher destroyed")

        self.robotPublisher = NetworkIO(
            True, walleyeData.teamNumber, walleyeData.tableName
        )

        Config.logger.info(f"Robot publisher created: {teamNumber} - {tableName}")

    def setPose(self,identifier, pose):
        self.poses[identifier] = f"Translation: {round(pose.X(), 2)}, {round(pose.Y(), 2)}, {round(pose.Z(), 2)} - Rotation: {round(pose.rotation().X(), 2)}, {round(pose.rotation().Y(), 2)}, {round(pose.rotation().Z(), 2)}"

    def getCalFilePaths(self):
        return {i.identifier: i.calibrationPath for i in self.cameras.info.values()}
    
    def setIP(self, ip):
        Config.logger.info("Attempting to set static IP")
        if not os.system(f"sudo ifconfig eth0 {ip} netmask 255.255.255.0"):
            Config.logger.info(f"Static IP set: {ip}")
            self.ip = ip
        else:
            Config.logger.error(f"Failed to set static ip: {ip}")

    @staticmethod
    def resetNetworking():
        if not os.system("sudo ifconfig eth0 down"):
            if not os.system("sudo ifconfig eth0 up"):
                Config.logger.info("Networking reset successful - IP might not be static")
            else:
                Config.logger.error("Networking failed to restart")
        else:
            Config.logger.error("Networking failed to stop")

    @staticmethod
    def getCurrentIP():
        return os.popen('ip addr show eth0 | grep "\<inet\>"').read().split()[1].split('/')[0].strip()
    
    def getState(self):
        return {
            "teamNumber": self.teamNumber,
            "tableName": self.tableName,
            "currentState": self.currentState.value,
            "cameraIDs": list(self.cameras.info.keys()),
            "cameraInCalibration": self.cameraInCalibration,
            "boardDims": self.boardDims,
            "calDelay": self.calDelay,
            "calImgPaths": self.calImgPaths,
            "reprojectionError": self.reprojectionError,
            "calFilePaths": self.getCalFilePaths(),
            "resolution": self.cameras.getResolutions(),
            "gain": self.cameras.getGains(),
            "exposure": self.cameras.getExposures(),
            "supportedResolutions": {
                k: v.supportedResolutions for k, v in self.cameras.info.items()
            },
            "ip" : self.ip,
        }


walleyeData = Config()
