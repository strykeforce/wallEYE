package WallEye;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * The data that the WallEye class will return when asked for new poses. Each object has an
 * associated Pose, an associated timestamp as well as an associated camera.
 */
public class WallEyeTagResult extends WallEyeResult {
  private final List<Tag> tags;
  private final double[] tagAreas;
  private final List<Point> centers;

  /**
   * Creates a WallEyeTagResult object with associated tag data.
   *
   * @param tagCorners The corner coordinates of the tags
   * @param timeStamp The time the camera captured this data
   * @param originCam The index of the camera that captured this data
   * @param updateNum The nth result from WallEye
   * @param numTags The number of tags in the image
   * @param tags The tag IDs detected in this image
   */
  public WallEyeTagResult(
      List<List<List<Double>>> tagCorners,
      double timeStamp,
      int originCam,
      int updateNum,
      int numTags,
      int[] tags) {

    super(timeStamp, originCam, updateNum, numTags, tags);

    if (tagCorners == null) {
      this.tags = Collections.emptyList();
      this.centers = Collections.emptyList();
      this.tagAreas = new double[0];
    } else {
      this.tags = new ArrayList<>(tagCorners.size());
      this.centers = new ArrayList<>(tagCorners.size());
      this.tagAreas = new double[tagCorners.size()];

      for (List<List<Double>> tagData : tagCorners) {
        Point[] corners = new Point[4];

        for (int i = 0; i < 4; i++) {
          corners[i] = new Point(tagData.get(i).get(0), tagData.get(i).get(1));
        }

        Tag tag = new Tag(corners);
        this.tags.add(tag);

        this.centers.add(tag.getCenter());
        this.tagAreas[this.tags.size() - 1] = tag.getArea();
      }
    }
  }

  public List<Tag> getTags() {
    return tags;
  }

  public List<Point> getTagCenters() {
    return centers;
  }

  public double[] getTagAreas() {
    return tagAreas;
  }

  @Override
  public String toString() {
    return "Update: " + updateNum + " | Tags: " + tags + " | Timestamp: " + timeStamp;
  }
}
