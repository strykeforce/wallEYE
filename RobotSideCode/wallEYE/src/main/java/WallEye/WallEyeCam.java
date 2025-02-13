package WallEye;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import edu.wpi.first.math.geometry.Pose3d;
import edu.wpi.first.math.geometry.Rotation3d;
import edu.wpi.first.math.geometry.Transform3d;
import edu.wpi.first.math.geometry.Translation3d;
import edu.wpi.first.networktables.BooleanSubscriber;
import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableInstance;
import edu.wpi.first.wpilibj.Notifier;
import edu.wpi.first.wpilibj.RobotController;
import java.util.List;
import java.util.function.DoubleSupplier;

/** A robot side code interface to interact and pull data from an Orange Pi running WallEye */
public class WallEyeCam {
  // Subscribers
  private BooleanSubscriber connectSub;

  private int curUpdateNum = 0;
  private Transform3d camToCenter;

  // Gyro
  private int dioPort = -1;
  private int currentGyroIndex = 0;
  private final int maxGyroResultSize = 100;
  private DoubleSupplier gyro;
  private DIOGyroResult[] gyroResults;
  private boolean hasTurnedOff;
  private Notifier dioLoop = new Notifier(this::grabGyro);

  // Camera
  private int camIndex = -1;
  private String camName;

  // Data
  private long timestamp = -1;
  private List<List<List<Double>>> tagCorners;
  private int[] tags;
  private WallEyeResult curData = new WallEyePoseResult(null, null, null, 0, 0, 0, 0, null, 0);
  private int newUpdateNum = 0;
  private static final Gson GSON = new Gson();

  /**
   * Creates a WallEye object that can pull pose location and timestamp data from Network Tables.
   *
   * @param tableName a string that specifies the table name of the WallEye instance (is set in the
   *     web interface)
   * @param camIndex number to identify the camera as according to webInterface
   * @param dioPort NOT IMPLEMENTED an int that corresponds to the dioport that the strobe is
   *     connected to (-1 to disable it)
   */
  public WallEyeCam(String tableName, int camIndex, int dioPort) {
    this.camName = tableName;
    this.camIndex = camIndex;

    gyroResults = new DIOGyroResult[maxGyroResultSize];
    hasTurnedOff = false;
    // this.gyro = gyro;

    if (dioPort > 0) {
      this.dioPort = dioPort;
      dioLoop.startPeriodic(0.05);
    }

    camToCenter = new Transform3d();

    NetworkTableInstance nt = NetworkTableInstance.getDefault();
    nt.startServer();

    NetworkTable table = nt.getTable(tableName);
    connectSub = table.getBooleanTopic("Connected" + camIndex).subscribe(false);
  }

  /** A method that checks the DIO port for an input and upon input will grab gyro and timestamp */
  private void grabGyro() {
    if (!hasTurnedOff) {
      gyroResults[currentGyroIndex] =
          new DIOGyroResult(0.0 /* gyro.getAsDouble() */, RobotController.getFPGATime());
      currentGyroIndex++;
      currentGyroIndex %= maxGyroResultSize;
      hasTurnedOff = true;
    } else {
      hasTurnedOff = false;
    }
  }

  /**
   * TESTME TESTME Check if the camera is still supplying images TESTME TESTME
   *
   * @return Returns a boolean (True : if and only if the Pi's supplied images are new)
   */
  public boolean isCameraConnected() {
    return connectSub.get();
  }

  /**
   * Getter for the camera index
   *
   * @return Returns an integer value for the number of cameras attached to the pi as specified by
   *     intialization
   */
  public int getCameraIndex() {
    return camIndex;
  }

  public void processUDP(String rawDataString, long recievedTime) {
    // its all a json...
    // The json is formated as such
    // All data from a camera is under tablename + index number
    // The mode the camera is in is under "Mode"
    // The update number is under "Update"
    // In mode 0 pose1 and pose2 are under "Pose1" and "Pose2" respectively
    // Each axis in the pose is under "tX", "tY", "tZ", "rX", "rY", "rZ"
    // Pose ambiguity is under "Ambig"
    // The timestamp is under "Timestamp"
    // An array containing all tags is under "Tags"

    // System.out.println(this.udpPort + " " + rawDataString);

    if (rawDataString == null || rawDataString.isEmpty()) {
      return;
    }

    JsonObject data = JsonParser.parseString(rawDataString).getAsJsonObject();
    String camId = camName + camIndex;

    if (!data.has(camId)) {
      return; // No vision update
    }

    JsonObject dataCam = data.getAsJsonObject(camId);

    timestamp = recievedTime - (long) (dataCam.get("Timestamp").getAsDouble() * 1000);

    int mode = dataCam.get("Mode").getAsInt();
    tags = GSON.fromJson(dataCam.get("Tags").toString(), int[].class);
    tagCorners = parseTagArray(dataCam.get("TagCorners").toString());

    switch (mode) {
      case 0 -> processPoseMode(dataCam);
      case 1 -> processTagMode(dataCam);
    }
  }

  private void processPoseMode(JsonObject dataCam) {
    newUpdateNum = dataCam.get("Update").getAsInt();
    Pose3d pose1 = parsePose3d(dataCam.get("Pose1").getAsJsonObject());

    if (pose1 == null) {
      System.err.println(
          "POSE IS NULL POSE IS NULL POSE IS NULL POSE IS NULL POSE IS NULL POSE IS NULL POSE IS NULL");
      System.err.println(dataCam.toString());
      return;
    }

    Pose3d pose2 = parsePose3d(dataCam.get("Pose2").getAsJsonObject());
    double ambiguity = dataCam.get("Ambig").getAsDouble();

    curData =
        new WallEyePoseResult(
            pose1,
            pose2,
            tagCorners,
            timestamp,
            camIndex,
            newUpdateNum,
            tags.length,
            tags,
            ambiguity);
  }

  private void processTagMode(JsonObject dataCam) {
    newUpdateNum = dataCam.get("Update").getAsInt();
    curData =
        new WallEyeTagResult(tagCorners, timestamp, camIndex, newUpdateNum, tags.length, tags);
  }

  private List<List<List<Double>>> parseTagArray(String tagCornersJson) {
    return GSON.fromJson(
        tagCornersJson,
        new com.google.gson.reflect.TypeToken<List<List<List<Double>>>>() {}.getType());
  }

  private Pose3d parsePose3d(JsonObject poseData) {
    double tX = poseData.get("tX").getAsDouble();
    double tY = poseData.get("tY").getAsDouble();
    double tZ = poseData.get("tZ").getAsDouble();
    double rX = poseData.get("rX").getAsDouble();
    double rY = poseData.get("rY").getAsDouble();
    double rZ = poseData.get("rZ").getAsDouble();

    return new Pose3d(new Translation3d(tX, tY, tZ), new Rotation3d(rX, rY, rZ));
  }

  /**
   * Returns WallEyeResult object with the corresponding data
   *
   * @return Most recent WallEyeResult
   */
  public WallEyeResult getResults() {
    curUpdateNum = curData.getUpdateNum();

    return curData;
  }

  /**
   * A method that will go back until it gets a timestamp from before the time reported by network
   * tables *should return more accurate timestamp measurements*
   *
   * @param timestamp a long that is the timestamp of the camera that is being searched for
   * @param camIndex an index that corresponds to the camera index
   * @param yaw a yaw that can be returned if it fails
   * @return Returns a DIOGyroResult with the data of the strobe result
   */
  public DIOGyroResult findGyro(long timestamp, int camIndex, double yaw) {
    int index = currentGyroIndex - 1;

    if (index < 0) {
      index += maxGyroResultSize;
    }

    while ((long) gyroResults[index].getTimestamp() > timestamp) {
      index--;

      if (index < 0) {
        index += maxGyroResultSize;
      }
      if (index == currentGyroIndex) {
        return new DIOGyroResult(yaw, timestamp);
      }
    }
    return gyroResults[index];
  }

  /**
   * Getter for the current update number
   *
   * @return Returns the current update number
   */
  public int getUpdateNumber() {
    return (int) newUpdateNum;
  }

  /**
   * Check if there is a new update in Network Tables for WallEye
   *
   * @return true if there is an update, false if not
   */
  public boolean hasNewUpdate() {
    return curUpdateNum != (int) newUpdateNum;
  }

  /**
   * Sets the translation for the camera to the center of the robot
   *
   * @param translation The Transform3d of camera to the center of the robot when the robot has not
   *     turned
   */
  public void setCamToCenter(Transform3d translation) {
    camToCenter = translation;
  }

  /**
   * Gets the pose for the center of the robot from a camera pose
   *
   * @param camPose the pose as returned by the camera
   * @return returns the pose from the center of the robot
   */
  public Pose3d camPoseToCenter(Pose3d camPose) {
    return camToCenter != null
        ? camPose.transformBy(camToCenter)
        : new Pose3d(new Translation3d(2767.0, 2767.0, 2767.0), new Rotation3d());
  }
}
