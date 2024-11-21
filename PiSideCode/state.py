from enum import Enum
import json
from camera.camera import Cameras
from camera.camera_info import CameraInfo
from directory import CONFIG_DATA_PATH
from publisher.network_table_publisher import NetworkIO
from calibration.calibration import CalibType
import logging
import socket
from networking import set_ip, get_current_ip
import wpimath.geometry as wpi
import os
import numpy as np


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
        self.should_update_web_stream = False
        self.ip: str = "10.27.67.99"

        self.visualizing_poses: bool = False

        self.loop_time: float = 2767.0
        self.cam_read_delay: dict[str:float] | None = None

        # Calibration
        self.calibration_type: CalibType = CalibType.CIRCLE_GRID
        self.camera_in_calibration: str | None = None
        self.board_dims: tuple[int, int] = (7, 7)
        self.cal_delay: float = 1
        self.cal_img_paths: list[str] = []
        self.reprojection_error: float | None = None

        # Cams
        self.cameras: Cameras = None

        self.robot_publisher: NetworkIO = None

        self.img_info: dict[str, str] = {}
        self.cam_nicknames: dict[str, str] = {}

        # SolvePNP
        self.valid_tags = np.arange(1, 17)
        self.tag_size = 0.157
        self.udp_port = 5802

        os.system(
            'nmcli --terse connection show | cut -d : -f 1 | while read name; do echo nmcli connection delete "$name"; done'
        )

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
                self.valid_tags = np.asarray(config["ValidTags"])
                self.cam_nicknames = config["Nicknames"]

                self.set_ip(ip)

                if get_current_ip() != ip:
                    Data.logger.warning("Failed to set static ip, trying again...")
                    self.set_ip(ip)

        # If no system file is found boot with base settings and create system
        # settings
        except (FileNotFoundError, json.decoder.JSONDecodeError, KeyError):
            Data.logger.error(f"Failed to load system data, setting defaults!")
            self.team_number = 2767
            self.table_name = "WallEye"
            self.ip = get_current_ip()
            Data.logger.info(f"IP is {self.ip}")

            self.make_publisher(self.team_number, self.table_name, self.udp_port)

            data_dump = {
                "TeamNumber": self.team_number,
                "TableName": self.table_name,
                "ip": self.ip,
                "BoardDim": self.board_dims,
                "TagSize": self.tag_size,
                "Port": self.udp_port,
                "ValidTags": self.valid_tags.tolist(),
                "Nicknames": {},
            }
            with open(CONFIG_DATA_PATH, "w") as out:
                json.dump(data_dump, out)

    def board_dims(self, new_value: tuple[int, int]):
        self.board_dims = new_value

    # Create a new robot publisher and create an output file for the data
    def make_publisher(self, team_number: int, table_name: str, port: int):
        Data.logger.info(
            f"Making publisher {table_name} for team {team_number} with UDP port {port}"
        )
        try:
            # Create and write output file
            with open(CONFIG_DATA_PATH, "r") as file:
                config = json.load(file)
                config["TeamNumber"] = team_number
                config["TableName"] = table_name
                config["Port"] = port
                with open(CONFIG_DATA_PATH, "w") as out:
                    json.dump(config, out)

            Data.logger.info(f"Publisher information written to {CONFIG_DATA_PATH}")

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
            False, self.team_number, self.table_name, self.udp_port, 2
        )

        Data.logger.info(f"Robot publisher created: {team_number} - {table_name}")

    def set_web_img_info(self, identifier: str, info: tuple[wpi.Pose3d] | list):
        if len(info) > 0 and isinstance(info[0], wpi.Pose3d):
            a, b = info
            self.img_info[
                identifier
            ] = f"Pose: [({round(a.X(), 2)}, {round(a.Y(), 2)}, {round(a.Z(), 2)}) ({round(a.rotation().X(), 2)}, {round(a.rotation().Y(), 2)}, {round(a.rotation().Z(), 2)})], ({round(b.X(), 2)}, {round(b.Y(), 2)}, {round(b.Z(), 2)}) ({round(b.rotation().X(), 2)}, {round(b.rotation().Y(), 2)}, {round(b.rotation().Z(), 2)})"

        elif isinstance(info, list):
            self.img_info[
                identifier
            ] = f"Tag centers: {np.array_str(np.asarray(info), precision=1, suppress_small=True)}"

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

        except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
            Data.logger.error(f"Failed to write Dimensions {dim}: {e}")

    # Set the udp port and save it off
    def set_udp_port(self, port):
        try:
            # Write it in system settings file
            with open(CONFIG_DATA_PATH, "r") as file:
                config = json.load(file)
                config["Port"] = port
                self.udp_port = port

                with open(CONFIG_DATA_PATH, "w") as out:
                    json.dump(config, out)

            self.make_publisher(self.team_number, self.table_name, self.udp_port)

        except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
            Data.logger.error(f"Failed to write port {port}: {e}")

    # Set Tag Size (meters) and set it in system settings

    def set_tag_size(self, size: float):
        try:
            # Write it in system settings file
            with open(CONFIG_DATA_PATH, "r") as file:
                config = json.load(file)
                config["TagSize"] = size
                with open(CONFIG_DATA_PATH, "w") as out:
                    json.dump(config, out)

        except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
            Data.logger.error(f"Failed to write tag size {size}: {e}")

    # Set static IP and write it into system files
    def set_ip(self, ip: str):
        if not ip:
            if not self.robot_publisher:
                self.make_publisher(self.team_number, self.table_name, self.udp_port)
            return

        # Destroy because changing IP breaks network tables
        if self.robot_publisher:
            self.robot_publisher.destroy()

        set_ip(ip)

        self.ip = get_current_ip()

        try:
            # Write IP to a system file
            with open(CONFIG_DATA_PATH, "r") as file:
                config = json.load(file)
                config["ip"] = self.ip
                with open(CONFIG_DATA_PATH, "w") as out:
                    json.dump(config, out)

        except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
            Data.logger.error(f"Failed to write static ip: {ip}: {e}")

        self.make_publisher(self.team_number, self.table_name, self.udp_port)

    def set_valid_tags(self, valid_tags: list):
        self.valid_tags = np.asarray(valid_tags)

        with open(CONFIG_DATA_PATH, "r") as file:
            config = json.load(file)
            config["ValidTags"] = valid_tags
            with open(CONFIG_DATA_PATH, "w") as out:
                json.dump(config, out)

    def set_nickname(self, identifier: str, nickname: str):
        self.cam_nicknames[identifier] = nickname

        with open(CONFIG_DATA_PATH, "r") as file:
            config = json.load(file)
            config["Nicknames"][identifier] = nickname
            with open(CONFIG_DATA_PATH, "w") as out:
                json.dump(config, out)

    def get_state(self) -> dict:
        return {
            "teamNumber": self.team_number,
            "tableName": self.table_name,
            "currentState": self.current_state.value,
            "cameraIDs": list(self.cameras.info.keys()),
            "cameraInCalibration": self.camera_in_calibration,
            "calibrationType": self.calibration_type.value,
            "boardDims": self.board_dims,
            "calDelay": self.cal_delay,
            "calImgPaths": self.cal_img_paths,
            "reprojectionError": self.reprojection_error,
            "calFilePaths": self.get_cal_file_paths(),
            "cameraConfigs": {
                identifier: camera_info.export_configs()
                for identifier, camera_info in self.cameras.info.items()
            },
            "cameraConfigOptions": {
                identifier: camera_info.export_config_options()
                for identifier, camera_info in self.cameras.info.items()
            },
            "ip": self.ip,
            "tagSize": self.tag_size,
            "udpPort": self.udp_port,
            "visualizingPoses": self.visualizing_poses,
            "status": self.status,
            "tagsAllowed": self.valid_tags.tolist(),
            "camNicknames": self.cam_nicknames,
        }


walleye_data = Data()
