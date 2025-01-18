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
  private List<Double> tagAreas = new ArrayList<>();

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
        center.add(
            (tag.get(0).get(0) + tag.get(1).get(0) + tag.get(2).get(0) + tag.get(3).get(0)) / 4.0);
        center.add(
            (tag.get(0).get(1) + tag.get(1).get(1) + tag.get(2).get(1) + tag.get(3).get(1)) / 4.0);
        this.centers.add(center);

        this.tagAreas.add(
            Math.abs(tag.get(0).get(0) - tag.get(2).get(0))
                * Math.abs(tag.get(0).get(1) - tag.get(2).get(1)));
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

  public List<Double> getTagAreas() {
    return tagAreas;
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
