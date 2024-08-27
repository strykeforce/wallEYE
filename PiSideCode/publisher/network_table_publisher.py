import ntcore
import logging
import wpimath.geometry as wpi
import socket
import struct
import json

from time import clock_gettime_ns, CLOCK_MONOTONIC


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
        self.pose1_sub = []
        self.pose2_sub = []
        self.timestamp_sub = []
        self.ambiguity_sub = []
        self.tag_sub = []
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
            self.publishers.append(self.table.getSubTable("Result" + str(index)))

            self.pose1_sub.append(
                self.publishers[index]
                .getDoubleArrayTopic("Pose1")
                .publish(
                    ntcore.PubSubOptions(
                        periodic=0.01, sendAll=True, keepDuplicates=True
                    )
                )
            )

            self.timestamp_sub.append(
                self.publishers[index]
                .getDoubleTopic("timestamp")
                .publish(
                    ntcore.PubSubOptions(
                        periodic=0.01, sendAll=True, keepDuplicates=True
                    )
                )
            )

            self.pose2_sub.append(
                self.publishers[index]
                .getDoubleArrayTopic("Pose2")
                .publish(
                    ntcore.PubSubOptions(
                        periodic=0.01, sendAll=True, keepDuplicates=True
                    )
                )
            )

            self.ambiguity_sub.append(
                self.publishers[index]
                .getDoubleTopic("ambiguity")
                .publish(
                    ntcore.PubSubOptions(
                        periodic=0.01, sendAll=True, keepDuplicates=True
                    )
                )
            )

            self.tag_sub.append(
                self.publishers[index]
                .getIntegerArrayTopic("tags")
                .publish(
                    ntcore.PubSubOptions(
                        periodic=0.01, sendAll=True, keepDuplicates=True
                    )
                )
            )

            self.publish_update.append(
                self.table.getIntegerTopic("Update" + str(index)).publish(
                    ntcore.PubSubOptions(
                        periodic=0.01, sendAll=True, keepDuplicates=True
                    )
                )
            )
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

    def udp_pose_publish(self, pose1, pose2, ambig, timestamp, tags):
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

    def pose_to_byte(self, pose):
        t = pose.translation()
        r = pose.rotation()
        axes = [t.X(), t.Y(), t.Z(), r.X(), r.Y(), r.Z()]
        byte_arr = []
        for axis in axes:
            byte_arr += bytearray(struct.pack("d", axis))
        return byte_arr

    # Publishes the supplied pose information in the corresponding publisher
    def publish(
        self,
        index: int,
        time: int,
        pose: wpi.Pose3d,
        tags: list[int],
        ambig: list[float],
    ):
        pose1 = pose[0]
        pose2 = pose[1]
        t1 = pose1.translation()
        r1 = pose1.rotation()
        t2 = pose2.translation()
        r2 = pose2.rotation()

        self.pose1_sub[index].set([t1.X(), t1.Y(), t1.Z(), r1.X(), r1.Y(), r1.Z()])
        self.pose2_sub[index].set([t2.X(), t2.Y(), t2.Z(), r2.X(), r2.Y(), r2.Z()])
        self.ambiguity_sub[index].set(ambig)
        self.tag_sub[index].set(tags)
        self.timestamp_sub[index].set(
            ntcore._now() - (clock_gettime_ns(CLOCK_MONOTONIC) / 1000000 - time) * 1000
        )

        self.update_num[index] += 1
        self.publish_update[index].set(self.update_num[index])

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
