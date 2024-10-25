package WallEye;

import java.util.ArrayList;

/**
 * The data that the WallEye class will return when asked for new poses. Each object has an
 * associated Pose, an associated timestamp as well as an associated camera.
 *
 * @see WallEye
 */
public class WallEyeTagResult extends WallEyeResult {
  private ArrayList<ArrayList<Double[]>> tagCenters;

  /**
   * Creates a WallEyeTagResult object with an associated Tag centers, timestamp and what cam
   * produced this
   *
   * @param pose1 the first pose that the SolvePNP returned
   * @param pose2 the second pose that the SolvePNP returned
   * @param ambiguity a double that represents to confidence of the pose
   */
  public WallEyeTagResult(
      ArrayList<ArrayList<Double[]>> tagCenters,
      double timeStamp,
      int originCam,
      int updateNum,
      int numTags,
      int[] tags) {

    super(timeStamp, originCam, updateNum, numTags, tags);

    this.tagCenters = tagCenters;
  }

  /**
   * Getter for the tag centers array
   *
   * @return int[][] of the tag centers
   */
  public ArrayList<ArrayList<Double[]>> getTagCenters() {
    return tagCenters;
  }

  @Override
  public String toString() {
    return "Update: "
        + updateNum
        + " | Tag Centers: "
        + tagCenters.toString()
        + " | Timestamp: "
        + timeStamp;
  }
}
