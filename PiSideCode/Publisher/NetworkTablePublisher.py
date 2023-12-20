import ntcore
import logging


class NetworkIO:
    logger = logging.getLogger(__name__)

    # Create a Network Tables Client with given info
    def __init__(self, test, team, tableName):
        # Grab the default network table instance and grab the table name
        self.inst = ntcore.NetworkTableInstance.getDefault()
        self.table = self.inst.getTable(tableName)

        # Start the WallEye_Client and set server depending on testing
        self.inst.startClient4("WallEye_Client")
        self.updateNum = []
        self.connection = []
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
        for index in range(5):
            self.publishers.append(
                self.table.getDoubleArrayTopic("Result" + str(index)).publish(
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

    # Publishes the supplied pose information in the corresponding publisher
    def publish(self, index, time, pose, tags, ambig):
        t = pose.translation()
        r = pose.rotation()
        result = [
            t.X(),
            t.Y(),
            t.Z(),
            r.X(),
            r.Y(),
            r.Z(),
            ntcore._now() - float(time),
            len(tags),
        ]
        for i in range(len(tags)):
            result.append(tags[i])
        result.append(ambig)
        self.publishers[index].set(result)
        self.updateNum[index] += 1
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
