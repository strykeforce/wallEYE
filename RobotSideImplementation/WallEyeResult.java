package frc.robot.subsystems;

import edu.wpi.first.math.geometry.Pose3d;

public class WallEyeResult {
    Pose3d cameraPose;
    double timeStamp;
    public WallEyeResult(Pose3d pose, double timeStamp) {
        cameraPose = pose;
        this.timeStamp = timeStamp;
    }

    public Pose3d getCameraPose() {
        return cameraPose;
    }

    public double getTimeStamp() {
        return timeStamp;
    }

}
