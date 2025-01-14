package WallEye;

/**
 * The data that the WallEye class will return when asked for new poses. Each object has an
 * associated Pose, an associated timestamp as well as an associated camera.
 *
 * @see WallEye
 */
public abstract class WallEyeResult {
  protected double timeStamp;
  protected int updateNum;
  protected int numTags;
  protected int originCam;
  protected int[] tags;

  /**
   * Creates a WallEyeResult object, timestamp and what cam produced this result
   *
   * @param timeStamp the time that NetworkTables recieved the update
   * @param originCam the camera's index that gave this pose
   * @param updateNum the nth result from WallEye
   * @param numTags the number of tags in the pose
   * @param tags an array of tag ids that was used to calculate pose
   */
  public WallEyeResult(double timeStamp, int originCam, int updateNum, int numTags, int[] tags) {
    this.timeStamp = timeStamp;
    this.updateNum = updateNum;
    this.numTags = numTags;
    this.originCam = originCam;
    this.tags = tags;
  }

  /**
   * Getter for the timestamp
   *
   * @return timestamp of the result (IN MICROSECONDS)
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

  /**
   * @return String
   */
  @Override
  public String toString() {
    return "Update: " + updateNum + " Timestamp: " + timeStamp;
  }
}
