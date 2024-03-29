package WallEye;

import edu.wpi.first.math.geometry.Pose3d;

/**
 * The data that the WallEye class will return when asked for new poses. Each object has an
 * associated Pose, an associated timestamp as well as an associated camera.
 *
 * @see WallEye
 */
public class WallEyeResult {
  Pose3d cameraPose1;
  Pose3d cameraPose2;
  double timeStamp;
  int updateNum;
  int numTags;
  int originCam;
  int[] tags;
  double ambiguity;

  /**
   * Creates a WallEyeResult object with an associated Pose, timestamp and what cam produced this
   * pose
   *
   * @param pose1 the first pose that the SolvePNP returned
   * @param pose2 the second pose that the SolvePNP returned
   * @param timeStamp the time that NetworkTables recieved the update
   * @param originCam the camera's index that gave this pose
   * @param updateNum the nth result from WallEye
   * @param numTags the number of tags in the pose
   * @param tags an array of tag ids that was used to calculate pose
   * @param ambiguity a double that represents to confidence of the pose
   */
  public WallEyeResult(
      Pose3d pose1,
      Pose3d pose2,
      double timeStamp,
      int originCam,
      int updateNum,
      int numTags,
      int[] tags,
      double ambiguity) {
    cameraPose1 = pose1;
    cameraPose2 = pose2;
    this.timeStamp = timeStamp;
    this.updateNum = updateNum;
    this.numTags = numTags;
    this.originCam = originCam;
    this.tags = tags;
    this.ambiguity = ambiguity;
  }

  /**
   * Getter for the ambiguity
   *
   * @return double that represents pose confidence (higher is worse [1.0 is the max])
   */
  public double getAmbiguity() {
    return ambiguity;
  }
  /**
   * Getter for the pose
   *
   * @return Pose3d of the camera's pose (Will return first pose if given two pose solution)
   */
  public Pose3d getCameraPose() {
    return cameraPose1;
  }

  /**
   * Getter for the first pose
   *
   * @return Pose3d of the camera's first pose as given by SolvePNP
   */
  public Pose3d getFirstPose() {
    return cameraPose1;
  }

  /**
   * Getter for the second pose
   *
   * @return Pose3d of the camera's second pose as given by SolvePNP
   */
  public Pose3d getSecondPose() {
    return cameraPose2;
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
}
