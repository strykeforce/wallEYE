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
    int updateNum;
    int numTags;
    int originCam;
    int[] tags;

    /**
     * Creates a WallEyeResult object with an associated Pose, timestamp and what cam produced this pose
     *   
     * @param pose the pose that the SolvePNP returned
     * @param timeStamp the time that NetworkTables recieved the update
     * @param originCam the camera's index that gave this pose
     * @param updateNum the nth result from WallEye
     * @param numTags the number of tags in the pose
     * @param tags an array of tag ids that was used to calculate pose
    */
    public WallEyeResult(Pose3d pose, double timeStamp, int originCam, int updateNum, int numTags, int[] tags) {
        cameraPose = pose;
        this.timeStamp = timeStamp;
        this.updateNum = updateNum;
        this.numTags = numTags;
        this.originCam = originCam;
        this.tags = tags;
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

    /**
     * Getter for the update number
     *   
     * @return the update number of this result
    */
    public int getUpdateNum() {
        return updateNum;
    }

    /**
     * Getter for the number of tags
     *   
     * @return the number of tags
    */
    public int getNumTags() {
        return numTags;
    }

    /**
     * Getter for the tag id array
     *   
     * @return array of ids used for pose calculation
    */
    public int[] getTagIDs() {
        return tags;
    }
}