import ntcore
import logging
import socket
import struct
import json

class NetworkIO:
    logger = logging.getLogger(__name__)

    # Create a Network Tables Client with given info
    def __init__(self, test, team, tableName, port, numCams):
        # Grab the default network table instance and grab the table name
        self.inst = ntcore.NetworkTableInstance.getDefault()
        self.table = self.inst.getTable(tableName)
        self.name = tableName
        self.robotIP = "10.27.67.2"
        self.robotPort = int(port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Start the WallEye_Client and set server depending on testing
        self.inst.startClient4("WallEye_Client")
        self.updateNum = []
        self.connection = []
        self.pose1Sub = []
        self.pose2Sub = []
        self.timestampSub = []
        self.ambiguitySub = []
        self.tagSub = []
        if test:
            self.inst.setServer("127.0.0.1", 5810)
        else:
            self.inst.setServerTeam(team)

        # Set all the publishers and update publishers
        self.publishers = []

        # Update publisher
        self.publishUpdate = []

        # image publisher ie has recieved a new image
        self.publishConnection = []

        # Pose publisher
        for index in range(numCams):
            self.publishers.append(self.table.getSubTable("Result" + str(index)))

            self.pose1Sub.append(self.publishers[index].getDoubleArrayTopic("Pose1").publish(
                    ntcore.PubSubOptions(
                        periodic=0.01, sendAll=True, keepDuplicates=True
                    )
                )
            )

            self.timestampSub.append(self.publishers[index].getDoubleTopic("timestamp").publish(
                    ntcore.PubSubOptions(
                        periodic=0.01, sendAll=True, keepDuplicates=True
                    )
                )
            )

            self.pose2Sub.append(self.publishers[index].getDoubleArrayTopic("Pose2").publish(
                    ntcore.PubSubOptions(
                        periodic=0.01, sendAll=True, keepDuplicates=True
                    )
                )
            )

            self.ambiguitySub.append(self.publishers[index].getDoubleTopic("ambiguity").publish(
                    ntcore.PubSubOptions(
                        periodic=0.01, sendAll=True, keepDuplicates=True
                    )
                )
            )

            self.tagSub.append(self.publishers[index].getIntegerArrayTopic("tags").publish(
                    ntcore.PubSubOptions(
                        periodic=0.01, sendAll=True, keepDuplicates=True
                    )
                )
            )

            self.publishUpdate.append(
                self.table.getIntegerTopic("Update" + str(index)).publish(
                    ntcore.PubSubOptions(
                        periodic=0.01, sendAll=True, keepDuplicates=True
                    )
                )
            )
            self.publishConnection.append(
                self.table.getBooleanTopic("Connected" + str(index)).publish(
                    ntcore.PubSubOptions(
                        periodic=0.01, sendAll=True, keepDuplicates=True
                    )
                )
            )

            self.updateNum.append(0)
            self.connection.append(False)

    def getTime(self):
        return ntcore._now()

    def setTable(self, name):
        self.table = self.inst.getTable(name)

    def udpPosePublish(self, pose1, pose2, ambig, timestamp, tags):
        dataDict = {}

        for i in range(len(pose1)):
            self.updateNum[i] += 1
            camDict = {}
            camDict["Mode"] = str(0)
            camDict["Update"] = str(self.updateNum[i])
            camDict["Pose1"] = self.poseToDict(pose1[i])
            camDict["Pose2"] = self.poseToDict(pose2[i])
            camDict["Ambig"] = str(ambig[i])
            camDict["Timestamp"] = str(ntcore._now() - timestamp[i])
            camDict["Tags"] = str(tags[i])
            dataDict[self.name + str(i)] = camDict
        dataString = json.dumps(dataDict)
        # self.logger.info(dataString)
        self.sock.sendto(bytes(dataString, "utf-8"), (self.robotIP, self.robotPort))

    def poseToDict(self, pose):
        t = pose.translation()
        r = pose.rotation()
        poseDict = {}
        poseDict["tX"] = str(t.X())
        poseDict["tY"] = str(t.Y())
        poseDict["tZ"] = str(t.Z())
        poseDict["rX"] = str(r.X())
        poseDict["rY"] = str(r.Y())
        poseDict["rZ"] = str(r.Z())
        return poseDict
        
    def poseToByte(self, pose):
        t = pose.translation()
        r = pose.rotation()
        axes = [t.X(), t.Y(), t.Z(), r.X(), r.Y(), r.Z()]
        byteArr = []
        for axis in axes:
            byteArr += bytearray(struct.pack("d", axis))
        return byteArr

    # Publishes the supplied pose information in the corresponding publisher
    def publish(self, index, time, pose, tags, ambig):
        pose1 = pose[0]
        pose2 = pose[1]
        t1 = pose1.translation()
        r1 = pose1.rotation()
        t2 = pose2.translation()
        r2 = pose2.rotation()

        self.pose1Sub[index].set([t1.X(), t1.Y(), t1.Z(), r1.X(), r1.Y(), r1.Z()])
        self.pose2Sub[index].set([t2.X(), t2.Y(), t2.Z(), r2.X(), r2.Y(), r2.Z()])
        self.ambiguitySub[index].set(ambig)
        self.tagSub[index].set(tags)
        self.timestampSub[index].set(ntcore._now() - time)

        # self.updateNum[index] += 1
        self.publishUpdate[index].set(self.updateNum[index])

    # Publish a new update number
    def increaseUpdateNum(self):
        self.updateNum += 1
        self.publishUpdate.set(self.updateNum)

    def setConnectionValue(self, index, val):
        self.connection[index] = val
        self.publishConnection[index].set(val)

    def getConnectionValue(self, index):
        return self.connection[index]

    def destroy(self):
        self.inst.stopClient()

    def updateTeam(self, num):
        self.inst.setServerTeam(num)

    def updateName(self, name):
        self.inst.getTable(name)
