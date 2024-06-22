from enum import Enum
import json
from camera.camera import Cameras
from camera.camera_info import CameraInfo
from directory import CONFIG_DATA_PATH
from publisher.network_table_publisher import NetworkIO
import logging
import socket
import struct
import fcntl
import wpimath.geometry as wpi

SIOCSIFADDR = 0x8916
SIOCGIFADDR = 0x8915
SIOCSIFNETMASK = 0x891C
networking_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sockfd = networking_socket.fileno()


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

    def __init__(self):
        self.current_state: States = States.PROCESSING
        self.status: str = "Running"
        self.ip: str | None = None

        self.visualizing_poses: bool = False

        self.loop_time: float = 2767.0

        # Calibration
        self.camera_in_calibration: str | None = None
        self.board_dims: tuple[int, int] = (7, 7)
        self.cal_delay: float = 1
        self.cal_img_paths: list[str] = []
        self.reprojection_error: float | None = None

        # Cams
        self.cameras: Cameras = None

        self.robot_publisher: NetworkIO = None

        self.poses: dict[str, str] = {}

        # SolvePNP
        self.tag_size = 0.157
        self.udp_port = 5802

        try:
            # Open and load system settings
            with open(CONFIG_DATA_PATH, "r") as data:
                config = json.load(data)
                self.team_number = config["TeamNumber"]
                self.table_name = config["TableName"]
                ip = config["ip"]
                self.board_dims = config["BoardDim"]
                self.tag_size = config["TagSize"]
                self.udp_port = config["Port"]

                self.set_ip(ip)

                if Data.get_current_ip() != ip:
                    Data.logger.warning(
                        "Failed to set static ip, trying again...")
                    self.set_ip(ip)

        # If no system file is found boot with base settings and create system
        # settings
        except (FileNotFoundError, json.decoder.JSONDecodeError, KeyError):
            self.team_number = 2767
            self.table_name = "WallEye"
            self.ip = Data.get_current_ip()
            Data.logger.info(f"IP is {self.ip}")

            self.make_publisher(
                self.team_number, self.table_name, self.udp_port)

            data_dump = {
                "TeamNumber": self.team_number,
                "TableName": self.table_name,
                "ip": self.ip,
                "BoardDim": self.board_dims,
                "TagSize": self.tag_size,
                "Port": self.udp_port,
            }
            with open(CONFIG_DATA_PATH, "w") as out:
                json.dump(data_dump, out)

    def board_dims(self, new_value: tuple[int, int]):
        self.board_dims = new_value

    # Create a new robot publisher and create an output file for the data
    def make_publisher(self, team_number: int, table_name: str, port: int):
        Data.logger.info(
            f"Making publisher {table_name} for team {team_number} with UDP port {port}")
        try:
            # Create and write output file
            with open(CONFIG_DATA_PATH, "r") as file:
                config = json.load(file)
                config["TeamNumber"] = team_number
                config["TableName"] = table_name
                config["Port"] = port
                with open(CONFIG_DATA_PATH, "w") as out:
                    json.dump(config, out)

            Data.logger.info(
                f"Publisher information written to {CONFIG_DATA_PATH}")

        except (FileNotFoundError, json.decoder.JSONDecodeError):
            Data.logger.error(
                f"Failed to write TableName | {table_name} | or TeamNumber | {team_number} | or Port |{port}"
            )
        self.team_number = team_number
        self.table_name = table_name
        self.udp_port = port

        # Destroy any existing publisher
        if self.robot_publisher is not None:
            Data.logger.info("Destorying existing publisher")
            self.robot_publisher.destroy()
            Data.logger.info("Existing publisher destroyed")

        # Create the robot publisher
        Data.logger.info("Creating publisher")
        self.robot_publisher = NetworkIO(
            False, self.team_number, self.table_name, self.udp_port, 2)

        Data.logger.info(
            f"Robot publisher created: {team_number} - {table_name}")

    def set_pose(self, identifier: str, pose: wpi.Pose3d):
        self.poses[identifier] = (
            f"Translation: {round(pose.X(), 2)}, {round(pose.Y(), 2)}, {round(pose.Z(), 2)} - Rotation: {round(pose.rotation().X(), 2)}, {round(pose.rotation().Y(), 2)}, {round(pose.rotation().Z(), 2)}"
        )

    # Return the file path names for each camera
    def get_cal_file_paths(self):
        return {i.identifier: i.calibration_path for i in self.cameras.info.values()}

    # Set the calibration board dimensions and set it in system settings
    def set_board_dim(self, dim: tuple[int, int]):
        try:
            # Write it in system settings file
            with open(CONFIG_DATA_PATH, "r") as file:
                config = json.load(file)
                config["BoardDim"] = dim
                with open(CONFIG_DATA_PATH, "w") as out:
                    json.dump(config, out)

        except (FileNotFoundError, json.decoder.JSONDecodeError):
            Data.logger.error(f"Failed to write Dimensions {dim}")

    # Set the udp port and save it off
    def setUDPPort(self, port):
        try:
            # Write it in system settings file
            with open(CONFIG_DATA_PATH, "r") as file:
                config = json.load(file)
                config["Port"] = port
                self.udpPort = port
                with open("SystemData.json", "w") as out:
                    json.dump(config, out)

            self.makePublisher(self.teamNumber, self.tableName, self.udpPort)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            Data.logger.error(f"Failed to write port {port}")

    # Set the udp port and save it off

    def set_udp_port(self, port):
        try:
            # Write it in system settings file
            with open(CONFIG_DATA_PATH, "w+") as file:
                config = json.load(file)
                config["Port"] = port
                self.udp_port = port
                json.dump(config, file)

            self.make_publisher(
                self.team_number, self.table_name, self.udp_port)

        except (FileNotFoundError, json.decoder.JSONDecodeError):
            Data.logger.error(f"Failed to write port {port}")

    # Set Tag Size (meters) and set it in system settings

    def set_tag_size(self, size: float):
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
    def set_ip(self, ip: str, interface: str = "eth0"):
        Data.logger.info("Attempting to set static IP")

        if not ip:
            Data.logger.warning("IP is None")
            if not self.robot_publisher:
                self.make_publisher(
                    self.team_number, self.table_name, self.udp_port)
            return

        # Destroy because changing IP breaks network tables
        if self.robot_publisher:
            self.robot_publisher.destroy()

        # Set IP
        # os.system("/usr/sbin/ifconfig eth0 up")
        # if not os.system(
        #         f"/usr/sbin/ifconfig eth0 {ip} netmask 255.255.255.0"):
        #     Data.logger.info(f"Static IP set: {ip} =? {Data.get_current_ip()}")
        #     self.ip = ip
        # else:
        #     self.ip = Data.get_current_ip()
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
        try:
            fcntl.ioctl(networking_socket, SIOCSIFADDR, ifreq)
        except Exception as e:
            Data.logger.info(f"Failed to set IP address: {e}")

        Data.logger.info(f"Static IP set: {ip} =? {Data.get_current_ip()}")
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

        self.make_publisher(self.team_number, self.table_name, self.udp_port)

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
    def get_current_ip(interface: str = "eth0"):
        # https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib/9267833#9267833
        ifreq = struct.pack(
            b"16sH14s", interface.encode("utf-8"), socket.AF_INET, b"\x00" * 14
        )
        try:
            res = fcntl.ioctl(sockfd, SIOCGIFADDR, ifreq)
        except Exception as e:
            Data.logger.error(
                f"Could not get current IP - {e} - Returning None")
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

    def get_state(self) -> dict:
        return {
            "teamNumber": self.team_number,
            "tableName": self.table_name,
            "currentState": self.current_state.value,
            "cameraIDs": list(self.cameras.info.keys()),
            "cameraInCalibration": self.camera_in_calibration,
            "boardDims": self.board_dims,
            "calDelay": self.cal_delay,
            "calImgPaths": self.cal_img_paths,
            "reprojectionError": self.reprojection_error,
            "calFilePaths": self.get_cal_file_paths(),
            "resolution": self.cameras.get_resolutions(),
            "brightness": self.cameras.get_brightnesss(),
            "exposure": self.cameras.get_exposures(),
            "supportedResolutions": {
                k: v.get_supported_resolutions() for k, v in self.cameras.info.items()
            },
            "exposureRange": {
                k: v.exposure_range for k, v in self.cameras.info.items()
            },
            "brightnessRange": {
                k: v.brightness_range for k, v in self.cameras.info.items()
            },
            "ip": self.ip,
            "tagSize": self.tag_size,
            "udpPort": self.udp_port,
            "visualizingPoses": self.visualizing_poses,
            "status": self.status,
        }


walleye_data = Data()
