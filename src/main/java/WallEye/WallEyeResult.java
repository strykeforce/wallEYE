package WallEye;

import edu.wpi.first.math.geometry.Pose3d;

/**
 * The data that the WallEye class will return when asked for new poses.
 * Each object has an associated Pose, an associated timestamp as well as an associated camera.
 * 
 * @see WallEye
 */
public class WallEyeResult {
    Pose3d cameraPose;
    double timeStamp;
    int originCam;

    /**
     * Creates a WallEyeResult object with an associated Pose, timestamp and what cam produced this pose
     *   
     * @param pose the pose that the SolvePNP returned
     * @param timeStamp the time that NetworkTables recieved the update
     * @param originCam the camera's index that gave this pose
    */
    public WallEyeResult(Pose3d pose, double timeStamp, int originCam) {
        cameraPose = pose;
        this.timeStamp = timeStamp;
    }

    /**
     * Getter for the pose
     *   
     * @return Pose3d of the camera's pose
    */
    public Pose3d getCameraPose() {
        return cameraPose;
    }

    /**
     * Getter for the timestamp
     *   
     * @return timestamp of the result
    */
    public double getTimeStamp() {
        return timeStamp;
    }

    /**
     * Getter for the original camera
     *   
     * @return index of the camera
    */
    public int getCamIndex() {
        return originCam;
    }
}