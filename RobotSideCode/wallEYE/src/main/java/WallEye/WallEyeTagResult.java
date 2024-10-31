package WallEye;

import java.util.ArrayList;

/**
 * The data that the WallEye class will return when asked for new poses. Each object has an
 * associated Pose, an associated timestamp as well as an associated camera.
 *
 * @see WallEye
 */
public class WallEyeTagResult extends WallEyeResult {
  private ArrayList<Double[]> tagCenters;

  /**
   * Creates a WallEyeTagResult object with an associated Tag centers, timestamp and what cam
   * produced this
   *
   * @param tagCenters The image coordinates (height, width) of the tag centers
   * @param timeStamp The time the camera captured this data
   * @param originCam The index of the camera that captured this data
   * @param updateNum The nth result from wallEYE
   * @param numTags The number of tags in the image
   * @param tags The tag ids detected in this image
   */
  public WallEyeTagResult(
      ArrayList<Double[]> tagCenters,
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
  public ArrayList<Double[]> getTagCenters() {
    return tagCenters;
  }

  /**
   * @return String
   */
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
