from enum import Enum
import json
from directory import CONFIG_DATA_PATH
from publisher.network_table_publisher import NetworkIO
import logging
import os
import socket, struct, fcntl

SIOCSIFADDR = 0x8916
SIOCGIFADDR = 0x8915
SIOCSIFNETMASK = 0x891C
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sockfd = sock.fileno()


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


class Data:
    logger = logging.getLogger(__name__)

    def __init__(self) -> None:
        self.currentState = States.PROCESSING
        self.status = "Running"

        self.visualizingPoses = False

        self.loopTime = 2767.0

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

        # SolvePNP
        self.tagSize = 0.157

        try:
            # Open and load system settings
            with open(CONFIG_DATA_PATH, "r") as data:
                config = json.load(data)
                self.teamNumber = config["TeamNumber"]
                self.tableName = config["TableName"]
                ip = config["ip"]
                self.boardDims = config["BoardDim"]
                self.tagSize = config["TagSize"]

                self.setIP(ip)

                if Data.getCurrentIP() != ip:
                    Data.logger.warning(
                        "Failed to set static ip, trying again...")
                    self.setIP(ip)

        # If no system file is found boot with base settings and create system
        # settings
        except (FileNotFoundError, json.decoder.JSONDecodeError, KeyError):
            self.teamNumber = 2767
            self.tableName = "WallEye"
            self.ip = Data.getCurrentIP()
            Data.logger.info(f"IP is {self.ip}")

            dataDump = {
                "TeamNumber": self.teamNumber,
                "TableName": self.tableName,
                "ip": self.ip,
                "BoardDim": self.boardDims,
                "TagSize": self.tagSize,
            }
            with open(CONFIG_DATA_PATH, "w") as out:
                json.dump(dataDump, out)

    def boardDims(self, newValue):
        self.boardDims = newValue

    # Create a new robot publisher and create an output file for the data
    def makePublisher(self, teamNumber, tableName):
        try:
            # Create and write output file
            with open(CONFIG_DATA_PATH, "r") as file:
                config = json.load(file)
                config["TeamNumber"] = teamNumber
                config["TableName"] = tableName
                with open(CONFIG_DATA_PATH, "w") as out:
                    json.dump(config, out)

        except (FileNotFoundError, json.decoder.JSONDecodeError):
            Data.logger.error(
                f"Failed to write TableName | {tableName} | or TeamNumber | {teamNumber} |"
            )
        self.teamNumber = teamNumber
        self.tableName = tableName

        # Destroy any existing publisher
        if self.robotPublisher is not None:
            self.robotPublisher.destroy()
            Data.logger.info("Existing publisher destroyed")

        # Create the robot publisher
        self.robotPublisher = NetworkIO(
            False, self.teamNumber, self.tableName, 2)

        Data.logger.info(
            f"Robot publisher created: {teamNumber} - {tableName}")

    def setPose(self, identifier, pose):
        self.poses[identifier] = (
            f"Translation: {round(pose.X(), 2)}, {round(pose.Y(), 2)}, {round(pose.Z(), 2)} - Rotation: {round(pose.rotation().X(), 2)}, {round(pose.rotation().Y(), 2)}, {round(pose.rotation().Z(), 2)}"
        )

    # Return the file path names for each camera
    def getCalFilePaths(self):
        return {i.identifier: i.calibrationPath for i in self.cameras.info.values()}

    # Set the calibration board dimensions and set it in system settings
    def setBoardDim(self, dim):
        try:
            # Write it in system settings file
            with open(CONFIG_DATA_PATH, "r") as file:
                config = json.load(file)
                config["BoardDim"] = dim
                with open(CONFIG_DATA_PATH, "w") as out:
                    json.dump(config, out)

        except (FileNotFoundError, json.decoder.JSONDecodeError):
            Data.logger.error(f"Failed to write Dimensions {dim}")

    # Set Tag Size (meters) and set it in system settings
    def setTagSize(self, size):
        try:
            # Write it in system settings file
            with open(CONFIG_DATA_PATH, "r") as file:
                config = json.load(file)
                config["TagSize"] = size
                with open(CONFIG_DATA_PATH, "w") as out:
                    json.dump(config, out)

        except (FileNotFoundError, json.decoder.JSONDecodeError):
            Data.logger.error(f"Failed to write tag size {size}")

    # Set static IP and write it into system files
    def setIP(self, ip, interface="wlp2s0"):
        Data.logger.info("Attempting to set static IP")

        if not ip:
            Data.logger.warning("IP is None")
            if not self.robotPublisher:
                self.makePublisher(self.teamNumber, self.tableName)
            return

        # Destroy because changing IP breaks network tables
        if self.robotPublisher:
            self.robotPublisher.destroy()

        # Set IP
        # os.system("/usr/sbin/ifconfig eth0 up")
        # if not os.system(
        #         f"/usr/sbin/ifconfig eth0 {ip} netmask 255.255.255.0"):
        #     Data.logger.info(f"Static IP set: {ip} =? {Data.getCurrentIP()}")
        #     self.ip = ip
        # else:
        #     self.ip = Data.getCurrentIP()
        #     Data.logger.error(f"Failed to set static ip: {ip}")
        # os.system("/usr/sbin/ifconfig eth0 up")

        # https://stackoverflow.com/questions/20420937/how-to-assign-ip-address-to-interface-in-python
        bin_ip = socket.inet_aton(ip)
        ifreq = struct.pack(
            b"16sH2s4s8s",
            interface.encode("utf-8"),
            socket.AF_INET,
            b"\x00" * 2,
            bin_ip,
            b"\x00" * 8,
        )
        # https://stackoverflow.com/questions/70310413/python-fcntl-ioctl-errno-1-operation-not-permitted
        fcntl.ioctl(sock, SIOCSIFADDR, ifreq)

        Data.logger.info(f"Static IP set: {ip} =? {Data.getCurrentIP()}")
        self.ip = ip

        try:
            # Write IP to a system file
            with open(CONFIG_DATA_PATH, "r") as file:
                config = json.load(file)
                config["ip"] = self.ip
                with open(CONFIG_DATA_PATH, "w") as out:
                    json.dump(config, out)

        except (FileNotFoundError, json.decoder.JSONDecodeError):
            Data.logger.error(f"Failed to write static ip: {ip}")

        self.makePublisher(self.teamNumber, self.tableName)

    # Obsolete
    # def resetNetworking(self):
    #     if not os.system("/usr/sbin/ifconfig eth0 down"):
    #         if not os.system("/usr/sbin/ifconfig eth0 up"):
    #             self.ip = Config.getCurrentIP()
    #             Config.logger.info(
    #                 f"Networking reset successful - IP might not be static: {self.ip}"
    #             )
    #         else:
    #             Config.logger.error("Networking failed to restart")
    #     else:
    #         Config.logger.error("Networking failed to stop")

    @staticmethod
    def getCurrentIP(interface="wlp2s0"):
        # https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib/9267833#9267833
        ifreq = struct.pack(
            b"16sH14s", interface.encode("utf-8"), socket.AF_INET, b"\x00" * 14
        )
        try:
            res = fcntl.ioctl(sockfd, SIOCGIFADDR, ifreq)
        except:
            Data.logger.error("Could not get current IP - Returning None")
            return None

        ip = struct.unpack("16sH2x4s8x", res)[2]
        return socket.inet_ntoa(ip)

        # try:
        #     return (
        #         os.popen('ip addr show eth0 | grep "\\<inet\\>"')
        #         .read()
        #         .split()[1]
        #         .split("/")[0]
        #         .strip()
        #     )
        # except IndexError:
        #     Data.logger.error("Could not get current IP - Returning None")
        #     return None

    def getState(self):
        return {
            "teamNumber": self.teamNumber,
            "tableName": self.tableName,
            "currentState": self.currentState.value,
            "cameraIDs": list(
                self.cameras.info.keys()),
            "cameraInCalibration": self.cameraInCalibration,
            "boardDims": self.boardDims,
            "calDelay": self.calDelay,
            "calImgPaths": self.calImgPaths,
            "reprojectionError": self.reprojectionError,
            "calFilePaths": self.getCalFilePaths(),
            "resolution": self.cameras.getResolutions(),
            "brightness": self.cameras.getBrightnesss(),
            "exposure": self.cameras.getExposures(),
            "supportedResolutions": {
                k: v.getSupportedResolutions() for k,
                v in self.cameras.info.items()},
            "exposureRange": {
                k: v.exposureRange for k,
                v in self.cameras.info.items()},
            "brightnessRange": {
                k: v.brightnessRange for k,
                v in self.cameras.info.items()},
            "ip": self.ip,
            "tagSize": self.tagSize,
            "visualizingPoses": self.visualizingPoses,
            "status": self.status,
        }


walleyeData = Data()
