from enum import Enum
import json
from Publisher.NetworkTablePublisher import NetworkIO
import logging
import os
import threading


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

walleyeDataLock = threading.Lock()


def threadsafe(function):
    def newFunction(*args, **kwargs):
        walleyeDataLock.acquire()
        function(*args, **kwargs)
        walleyeDataLock.release()

    return newFunction


class Config:
    logger = logging.getLogger(__name__)

    def __init__(self) -> None:
        self._currentState = States.PROCESSING

        self._visualizingPoses = False

        self._loopTime = 2767

        # Calibration
        self._cameraInCalibration = None
        self._boardDims = (7, 7)
        self._calDelay = 1
        self._calImgPaths = []
        self._reprojectionError = None

        # Cams
        self._cameras = None

        self._robotPublisher = None

        self._poses = {}

        # SolvePNP
        self._tagSize = 0.157

        try:
            with open("SystemData.json", "r") as data:
                config = json.load(data)
                self._teamNumber = config["TeamNumber"]
                self._tableName = config["TableName"]
                self._ip = config["ip"]
                self._boardDims = config["BoardDim"]
                self._tagSize = config["TagSize"]

                self.setIP(self.ip)

        except (FileNotFoundError, json.decoder.JSONDecodeError, KeyError):
            self._teamNumber = 2767
            self._tableName = "WallEye"
            try:
                self._ip = Config.getCurrentIP()
                Config.logger.info(f"IP is {self.ip}")
            except IndexError:
                Config.logger.error("Could not get current IP")
            dataDump = {
                "TeamNumber": self._teamNumber,
                "TableName": self._tableName,
                "ip": self._ip,
                "BoardDim": self._boardDims,
                "TagSize": self._tagSize,
            }
            with open("SystemData.json", "w") as out:
                json.dump(dataDump, out)

    @threadsafe
    @property
    def currentState(self):
        return self._currentState

    @threadsafe
    @currentState.setter
    def currentState(self, newValue):
        self._currentState = newValue

    @threadsafe
    @property
    def visualizingPoses(self):
        return self._visualizingPoses

    @threadsafe
    @visualizingPoses.setter
    def visualizingPoses(self, newValue):
        self._visualizingPoses = newValue

    @threadsafe
    @property
    def loopTime(self):
        return self._loopTime

    @threadsafe
    @loopTime.setter
    def loopTime(self, newValue):
        self._loopTime = newValue

    @threadsafe
    @property
    def cameraInCalibration(self):
        return self._cameraInCalibration

    @threadsafe
    @cameraInCalibration.setter
    def cameraInCalibration(self, newValue):
        self._cameraInCalibration = newValue

    @threadsafe
    @property
    def boardDims(self):
        return self._boardDims

    @threadsafe
    @boardDims.setter
    def boardDims(self, newValue):
        self._boardDims = newValue

    @threadsafe
    @property
    def calDelay(self):
        return self._calDelay

    @threadsafe
    @calDelay.setter
    def calDelay(self, newValue):
        self._calDelay = newValue

    @threadsafe
    @property
    def calImgPaths(self):
        return self.calImgPaths

    @threadsafe
    @calImgPaths.setter
    def calImgPaths(self, newValue):
        self._calImgPaths = newValue

    @threadsafe
    @property
    def reprojectionError(self):
        return self._reprojectionError

    @threadsafe
    @reprojectionError.setter
    def reprojectionError(self, newValue):
        self._reprojectionError = newValue

    @threadsafe
    @property
    def cameras(self):
        return self._cameras

    @threadsafe
    @cameras.setter
    def cameras(self, newValue):
        self._cameras = newValue

    @threadsafe
    @property
    def robotPublisher(self):
        return self._robotPublisher

    @threadsafe
    @robotPublisher.setter
    def robotPublisher(self, newValue):
        self._robotPublisher = newValue

    @threadsafe
    @property
    def poses(self):
        return self._poses

    @threadsafe
    @poses.setter
    def poses(self, newValue):
        self._poses = newValue

    @threadsafe
    @property
    def tagSize(self):
        return self._tagSize

    @threadsafe
    @tagSize.setter
    def tagSize(self, newValue):
        self._tagSize = newValue

    @threadsafe
    @property
    def teamNumber(self):
        return self._teamNumber

    @threadsafe
    @teamNumber.setter
    def teamNumber(self, newValue):
        self._teamNumber = newValue

    @threadsafe
    @property
    def tableName(self):
        return self._tableName

    @threadsafe
    @tableName.setter
    def tableName(self, newValue):
        self._tableName = newValue

    @threadsafe
    @property
    def ip(self):
        return self.ip

    @threadsafe
    @ip.setter
    def ip(self, newValue):
        self._ip = newValue

    @threadsafe
    @property
    def boardDims(self):
        return self._boardDims

    @threadsafe
    @boardDims.setter
    def boardDims(self, newValue):
        self._boardDims = newValue

    def makePublisher(self, teamNumber, tableName):
        try:
            with open("SystemData.json", "r") as file:
                config = json.load(file)
                config["TeamNumber"] = teamNumber
                config["TableName"] = tableName
                with open("SystemData.json", "w") as out:
                    json.dump(config, out)

        except (FileNotFoundError, json.decoder.JSONDecodeError):
            Config.logger.error(
                f"Failed to write TableName | {tableName} | or TeamNumber | {teamNumber} |"
            )
        self.teamNumber = teamNumber
        self.tableName = tableName

        if self.robotPublisher is not None:
            self.robotPublisher.destroy()
            Config.logger.info("Existing publisher destroyed")

        self.robotPublisher = NetworkIO(False, self.teamNumber, self.tableName)

        Config.logger.info(f"Robot publisher created: {teamNumber} - {tableName}")

    def setPose(self, identifier, pose):
        self.poses[
            identifier
        ] = f"Translation: {round(pose.X(), 2)}, {round(pose.Y(), 2)}, {round(pose.Z(), 2)} - Rotation: {round(pose.rotation().X(), 2)}, {round(pose.rotation().Y(), 2)}, {round(pose.rotation().Z(), 2)}"

    def getCalFilePaths(self):
        return {i.identifier: i.calibrationPath for i in self.cameras.info.values()}

    def setBoardDim(self, dim):
        try:
            with open("SystemData.json", "r") as file:
                config = json.load(file)
                config["BoardDim"] = dim
                with open("SystemData.json", "w") as out:
                    json.dump(config, out)

        except (FileNotFoundError, json.decoder.JSONDecodeError):
            Config.logger.error(f"Failed to write Dimensions {dim}")

    def setTagSize(self, size):
        try:
            with open("SystemData.json", "r") as file:
                config = json.load(file)
                config["TagSize"] = size
                with open("SystemData.json", "w") as out:
                    json.dump(config, out)

        except (FileNotFoundError, json.decoder.JSONDecodeError):
            Config.logger.error(f"Failed to write tag size {size}")

    def setIP(self, ip):
        Config.logger.info("Attempting to set static IP")
        # os.system("/usr/sbin/ifconfig eth0 down")
        # if not os.system(f"/usr/sbin/ifconfig eth0 {ip} netmask 255.255.255.0"):
        #     Config.logger.info(f"Static IP set: {ip}")
        #     self.ip = ip
        # else:
        #     self.ip = Config.getCurrentIP()
        #     Config.logger.error(f"Failed to set static ip: {ip}")
        # os.system("/usr/sbin/ifconfig eth0 up")

        if not os.system(f"nmcli connection modify eth0 ipv4.address {ip}/24"):
            Config.logger.info(f"Static IP set: {ip}")
            self.ip = ip
        else:
            self.ip = Config.getCurrentIP()
            Config.logger.error(f"Failed to set static ip: {ip}")
        os.system("nmcli connection up eth0")

        try:
            with open("SystemData.json", "r") as file:
                config = json.load(file)
                config["ip"] = self.ip
                with open("SystemData.json", "w") as out:
                    json.dump(config, out)

        except (FileNotFoundError, json.decoder.JSONDecodeError):
            Config.logger.error(f"Failed to write static ip: {ip}")

    def resetNetworking(self):
        if not os.system("/usr/sbin/ifconfig eth0 down"):
            if not os.system("/usr/sbin/ifconfig eth0 up"):
                self.ip = Config.getCurrentIP()
                Config.logger.info(
                    f"Networking reset successful - IP might not be static: {self.ip}"
                )
            else:
                Config.logger.error("Networking failed to restart")
        else:
            Config.logger.error("Networking failed to stop")

    @staticmethod
    def getCurrentIP():
        return (
            os.popen('ip addr show eth0 | grep "\<inet\>"')
            .read()
            .split()[1]
            .split("/")[0]
            .strip()
        )

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
            "ip": self.ip,
            "tagSize": self.tagSize,
            "visualizingPoses": self.visualizingPoses,
        }


walleyeData = Config()
