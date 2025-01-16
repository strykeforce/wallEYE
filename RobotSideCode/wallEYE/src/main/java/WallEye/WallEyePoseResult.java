package WallEye;

import edu.wpi.first.math.geometry.Pose3d;
import java.util.List;

/**
 * The data that the WallEye class will return when asked for new poses. Each object has an
 * associated Pose, an associated timestamp as well as an associated camera.
 *
 * @see WallEye
 */
public class WallEyePoseResult extends WallEyeTagResult {
  private Pose3d cameraPose1;
  private Pose3d cameraPose2;
  private double ambiguity;

  /**
   * Creates a WallEyePoseResult object with an associated Pose, timestamp and what cam produced
   * this pose
   *
   * @param pose1 One of the poses produced by SolvePnP
   * @param pose2 The other pose produced by SolvePnP
   * @param timeStamp The time the camera captured this data
   * @param originCam The camera's index that gave this data
   * @param updateNum The nth result from wallEYE
   * @param numTags The number of tags used to calculate these poses
   * @param tags List of tags used to calculate these poses
   * @param ambiguity Ambiguity of this result
   */
  public WallEyePoseResult(
      Pose3d pose1,
      Pose3d pose2,
      List<List<List<Double>>> tagCorners,
      double timeStamp,
      int originCam,
      int updateNum,
      int numTags,
      int[] tags,
      double ambiguity) {

    super(tagCorners, timeStamp, originCam, updateNum, numTags, tags);

    this.cameraPose1 = pose1;
    this.cameraPose2 = pose2;
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
   * @return String
   */
  @Override
  public String toString() {
    return "Update: " + updateNum + " | Pose1: " + cameraPose1 + " | Timestamp: " + timeStamp;
  }
}
