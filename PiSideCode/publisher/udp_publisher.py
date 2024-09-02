import ntcore
import logging
import wpimath.geometry as wpi
import socket
import struct
import json


class UdpPublisher:
    logger = logging.getLogger(__name__)

    # Create a Network Tables Client with given info
    def __init__(self, port: int, num_cams: int):
        self.robot_ip = "10.27.67.2"
        self.robot_port = int(port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.update_num = [0] * num_cams

    def get_time(self) -> int:
        return ntcore._now()

    def udp_pose_publish(
        self,
        pose1: wpi.Pose3d,
        pose2: wpi.Pose3d,
        ambig: list[float],
        timestamp: list[float],
        tags: list[int],
    ):
        data_dict = {}

        for i in range(len(pose1)):
            self.update_num[i] += 1
            camDict = {
                "Mode": "0",
                "Update": str(self.update_num[i]),
                "Pose1": self.pose_to_dict(pose1[i]),
                "Pose2": self.pose_to_dict(pose2[i]),
                "Ambig": str(ambig[i]),
                "Timestamp": str(ntcore._now() - timestamp[i]),
                "Tags": str(tags[i]),
            }
            data_dict[self.name + str(i)] = camDict
        data_str = json.dumps(data_dict)
        self.sock.sendto(bytes(data_str, "utf-8"), (self.robot_ip, self.robot_port))

    def pose_to_dict(self, pose: wpi.Pose3d):
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

    def pose_to_byte(self, pose: wpi.Pose3d):
        t = pose.translation()
        r = pose.rotation()
        axes = [t.X(), t.Y(), t.Z(), r.X(), r.Y(), r.Z()]
        byte_arr = []
        for axis in axes:
            byte_arr += bytearray(struct.pack("d", axis))
        return byte_arr

    # Publish a new update number
    def increase_update_num(self):
        self.update_num += 1
