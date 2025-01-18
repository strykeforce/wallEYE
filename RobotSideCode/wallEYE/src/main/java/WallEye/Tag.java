package WallEye;

public class Tag {
  private final Point[] corners; // Order is cw starting from bottom right

  public Tag(Point[] corners) {
    this.corners = corners;
  }

  public Point[] getCorners() {
    return corners;
  }

  public Point getCenter() {
    double centerX = 0.0, centerY = 0.0;

    for (Point corner : corners) {
      centerX += corner.x();
      centerY += corner.y();
    }
    return new Point(centerX / 4.0, centerY / 4.0);
  }

  public double getArea() {
    // Assume rectangle
    double width1 = Math.abs(corners[0].x() - corners[2].x());
    double height1 = Math.abs(corners[0].y() - corners[2].y());
    double width2 = Math.abs(corners[1].x() - corners[3].x());
    double height2 = Math.abs(corners[1].y() - corners[3].y());
    return (width1 * height1 + width2 * height2) / 2.0;
  }
}
