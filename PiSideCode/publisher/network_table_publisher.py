import ntcore
import logging
import socket
import struct
import json
from processing.pose_processing import PoseProcessor

import time

class NetworkIO:
    logger = logging.getLogger(__name__)

    # Create a Network Tables Client with given info
    def __init__(
        self, test: bool, team: int, table_name: str, port: int, num_cams: int
    ):
        # Grab the default network table instance and grab the table name
        self.inst = ntcore.NetworkTableInstance.getDefault()
        self.table = self.inst.getTable(table_name)
        self.name = table_name
        self.robot_ip = "10.27.67.2"
        self.robot_port = int(port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Start the WallEye_Client and set server depending on testing
        self.inst.startClient4("WallEye_Client")
        self.update_num = []
        self.connection = []
      
        if test:
            self.inst.setServer("127.0.0.1", 5810)
        else:
            self.inst.setServerTeam(team)

        # Set all the publishers and update publishers
        self.publishers = []

        # Update publisher
        self.publish_update = []

        # image publisher ie has recieved a new image
        self.publish_connection = []

        # Pose publisher
        for index in range(num_cams):
            self.publish_connection.append(
                self.table.getBooleanTopic("Connected" + str(index)).publish(
                    ntcore.PubSubOptions(
                        periodic=0.01, sendAll=True, keepDuplicates=True
                    )
                )
            )

            self.update_num.append(0)
            self.connection.append(False)

    def get_time(self) -> int:
        return ntcore._now()

    def set_table(self, name: str):
        self.table = self.inst.getTable(name)

    def udp_pose_publish(self, pose1, pose2, ambig, timestamps, tags, tag_corners):
        data_dict = {}

        for i in range(len(pose1)):
            if pose1[i] == PoseProcessor.BAD_POSE:
                continue

            self.update_num[i] += 1
            camDict = {
                "Mode": 0,
                "Update": self.update_num[i],
                "Pose1": self.pose_to_dict(pose1[i]),
                "Pose2": self.pose_to_dict(pose2[i]),
                "Ambig": ambig[i],
                # "Timestamp": str(ntcore._now() - timestamp[i]),
                "Timestamp": (time.monotonic_ns() / 1000000 - timestamps[i]),
                "Tags": tags[i].tolist(),
                "TagCorners": tag_corners[i].tolist(),
            }
            data_dict[self.name + str(i)] = camDict
        data_str = json.dumps(data_dict)

        try:
            self.sock.sendto(bytes(data_str, "utf-8"), (self.robot_ip, self.robot_port))
        except Exception as e:
            # NetworkIO.logger.error("Failed to publish pose in UDP: ", exc_info=e)
            pass

    def udp_tag_publish(self, tags, tag_corners, timestamps):
        data_dict = {}

        # Loop through each camera
        for i in range(len(tags)):
            if len(tags) == 0:
                continue

            self.update_num[i] += 1 

            # Data for camera i
            data_dict[self.name + str(i)] = {
                "Mode": 1,
                "Update": (self.update_num[i]),
                "Tags": tags[i].tolist(), 
                "TagCorners": tag_corners[i].tolist(),
                "Timestamp": (time.monotonic_ns() / 1000000 - timestamps[i]),
            }

        data_str = json.dumps(data_dict)

        try:
            self.sock.sendto(bytes(data_str, "utf-8"), (self.robot_ip, self.robot_port))
        except Exception as e:
            # NetworkIO.logger.error("Failed to publish pose in UDP: ", exc_info=e)
            pass

    def pose_to_dict(self, pose):
        t = pose.translation()
        r = pose.rotation()

        return {
            "tX": str(t.X()),
            "tY": str(t.Y()),
            "tZ": str(t.Z()),
            "rX": str(r.X()),
            "rY": str(r.Y()),
            "rZ": str(r.Z()),
        }

    # Publish a new update number
    def increase_update_num(self):
        self.update_num += 1
        self.publish_update.set(self.update_num)

    def set_connection_value(self, index: int, val):
        self.connection[index] = val
        self.publish_connection[index].set(val)

    def get_connection_value(self, index: int):
        return self.connection[index]

    def destroy(self):
        self.inst.stopClient()

    def update_team(self, num: int):
        self.inst.setServerTeam(num)

    def update_name(self, name: str):
        self.inst.getTable(name)
