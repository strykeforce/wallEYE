import ntcore
import wpimath.geometry as wpi

class NetworkIO:
    def __init__(self, test, team, tableName):
        self.inst = ntcore.NetworkTableInstance.getDefault()
        self.table = self.inst.getTable(tableName)
        self.inst.startClient4("WallEye_Client")
        if test:
            self.inst.setServer("127.0.0.1", 5810)
        else:
            self.inst.setServerTeam(team)

        self.publishers = []
        for index in range(5):
            self.publishers.append(self.table.getDoubleArrayTopic("Result" + str(index)).publish(ntcore.PubSubOptions(periodic=0.01, sendAll=True, keepDuplicates=True)))

    def getTime(self):
        return ntcore._now()

    def setTable(self, name):
        self.table = self.inst.getTable(name)

    def publish(self, index, time, pose):
        t = pose.translation()
        r = pose.rotation()
        result = [t.X(), t.Y(), t.Z(), r.X(), r.Y(), r.Z(), time]
        self.publishers[index].set(result)

    def destroy(self):
        self.inst.stopClient()

    def updateTeam(self, num):
        self.inst.setServerTeam(num)

    def updateName(self, name):
        self.inst.getTable(name)
