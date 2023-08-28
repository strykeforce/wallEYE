import ntcore
from timing import timer

class NetworkIO:
    def __init__(self, test, team, tableName):
        self.inst = ntcore.NetworkTableInstance.getDefault()
        self.table = self.inst.getTable(tableName)
        self.inst.startClient4("WallEye_Client")
        self.updateNum = 0
        if test:
            self.inst.setServer("127.0.0.1", 5810)
        else:
            self.inst.setServerTeam(team)

        self.publishers = []
        self.publishUpdate = self.table.getIntegerTopic("Update").publish(ntcore.PubSubOptions(periodic=0.01, sendAll=True, keepDuplicates=True))
        for index in range(5):
            self.publishers.append(self.table.getDoubleArrayTopic("Result" + str(index)).publish(ntcore.PubSubOptions(periodic=0.01, sendAll=True, keepDuplicates=True)))

    def getTime(self):
        return ntcore._now()

    def setTable(self, name):
        self.table = self.inst.getTable(name)

    @timer
    def publish(self, index, time, pose, tags, ambig):
        t = pose.translation()
        r = pose.rotation()
        result = [t.X(), t.Y(), t.Z(), r.X(), r.Y(), r.Z(), float(time), len(tags)]
        for i in range(len(tags)):
            result.append(tags[i]) # Optimize with extend?
        result.append(ambig)
        self.publishers[index].set(result)

    def increaseUpdateNum(self):
        self.updateNum += 1
        self.publishUpdate.set(self.updateNum)

    def destroy(self):
        self.inst.stopClient()

    def updateTeam(self, num):
        self.inst.setServerTeam(num)

    def updateName(self, name):
        self.inst.getTable(name)
