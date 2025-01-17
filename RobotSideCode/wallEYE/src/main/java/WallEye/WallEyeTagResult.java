package WallEye;

import java.util.ArrayList;
import java.util.List;

/**
 * The data that the WallEye class will return when asked for new poses. Each object has an
 * associated Pose, an associated timestamp as well as an associated camera.
 *
 * @see WallEye
 */
public class WallEyeTagResult extends WallEyeResult {
  private List<List<List<Double>>> tagCorners;
  private List<List<Double>> centers = new ArrayList<>();

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
      List<List<List<Double>>> tagCorners,
      double timeStamp,
      int originCam,
      int updateNum,
      int numTags,
      int[] tags) {

    super(timeStamp, originCam, updateNum, numTags, tags);

    this.tagCorners = tagCorners;

    if (tagCorners != null) {
      for (List<List<Double>> tag : tagCorners) {
        List<Double> center = new ArrayList<Double>();
        center.add((tag.get(0).get(0) + tag.get(2).get(0)) / 2.0);
        center.add((tag.get(0).get(1) + tag.get(2).get(1)) / 2.0);
        this.centers.add(center);
      }
    }
  }

  /**
   * Getter for the tag centers array
   *
   * @return int[][] of the tag centers
   */
  public List<List<List<Double>>> getTagCorners() {
    return tagCorners;
  }

  public List<List<Double>> getTagCenters() {
    return centers;
  }

  /**
   * @return String
   */
  @Override
  public String toString() {
    return "Update: "
        + updateNum
        + " | Tag Corners: "
        + tagCorners.toString()
        + " | Timestamp: "
        + timeStamp;
  }
}
