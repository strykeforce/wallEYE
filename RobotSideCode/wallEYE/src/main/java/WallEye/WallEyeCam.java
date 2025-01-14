package WallEye;

import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.reflect.TypeToken;
import edu.wpi.first.math.geometry.Pose3d;
import edu.wpi.first.math.geometry.Rotation3d;
import edu.wpi.first.math.geometry.Transform3d;
import edu.wpi.first.math.geometry.Translation3d;
import edu.wpi.first.networktables.BooleanSubscriber;
import edu.wpi.first.networktables.DoubleArraySubscriber;
import edu.wpi.first.networktables.DoubleSubscriber;
import edu.wpi.first.networktables.IntegerArraySubscriber;
import edu.wpi.first.networktables.IntegerSubscriber;
import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableInstance;
import edu.wpi.first.wpilibj.Notifier;
import edu.wpi.first.wpilibj.RobotController;
import java.lang.reflect.Type;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.DoubleSupplier;

/** A robot side code interface to interact and pull data from an Orange Pi running WallEye */
public class WallEyeCam {
  // Subscribers
  private DoubleArraySubscriber pose1Sub;
  private DoubleArraySubscriber pose2Sub;
  private DoubleSubscriber timestampSub;
  private DoubleSubscriber ambiguitySub;
  private IntegerArraySubscriber tagsSub;
  private BooleanSubscriber connectSub;
  private IntegerSubscriber updateSub;

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
  private List<List<Double>> tagCenters;
  private int[] tags;
  private WallEyeResult curData = new WallEyePoseResult(null, null, null, 0, 0, 0, 0, null, 0);
  private int newUpdateNum = 0;

  // Constants
  private final int kIntByteSize = 4;
  private final int kDoubleByteSize = 8;
  private final int kLongByteSize = 8;
  private final int kPoseByteSize = kDoubleByteSize * 6;
  private final int kFinalTagInt = -1;

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

    double[] def = {2767.0, 2767.0, 2767.0, 2767.0, 2767.0, 2767.0, 2767.0};
    long[] defInt = {-1};

    NetworkTable table = nt.getTable(tableName);
    NetworkTable subTable = table.getSubTable("Result" + camIndex);

    pose1Sub = subTable.getDoubleArrayTopic("Pose1").subscribe(def);
    pose2Sub = subTable.getDoubleArrayTopic("Pose2").subscribe(def);
    timestampSub = subTable.getDoubleTopic("timestamp").subscribe(0.0);
    ambiguitySub = subTable.getDoubleTopic("ambiguity").subscribe(1.0);
    tagsSub = subTable.getIntegerArrayTopic("tags").subscribe(defInt);

    updateSub = table.getIntegerTopic("Update" + camIndex).subscribe(0);
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

  public void processUDP(String rawDataString) {
    if (rawDataString == null) {
      return;
    }

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

    // try {
    JsonObject data =
        JsonParser.parseString(rawDataString)
            .getAsJsonObject(); // Could move to UDP subscriber for performance

    Map<String, JsonElement> dataMap = data.asMap();

    String camId = camName + camIndex;

    if (!dataMap.containsKey(camId)) {
      // System.err.println("Exiting, no data for " + camId);
      // System.err.println(rawDataString);
      return; // No vision update
    }

    // System.out.println(rawDataString);
    // System.out.println("Want " + camName + camIndex);
    Map<String, JsonElement> dataCam = dataMap.get(camId).getAsJsonObject().asMap();
    if (dataCam != null) {
      int mode = dataCam.get("Mode").getAsInt();

      timestamp =
          RobotController.getFPGATime()
              - (long) (dataCam.get("Timestamp").getAsDouble() * 1000); // Recieved ms, want us

      ArrayList<Integer> parsedTagIds = new ArrayList<Integer>();

      for (String s :
          dataCam
              .get("Tags")
              .toString()
              .replace("\"", "")
              .replace("]", "")
              .replace("[", "")
              .split("\\s+")) {
        if (!s.isEmpty()) {
          parsedTagIds.add(Integer.parseInt(s));
        }
      }
      tags = new int[parsedTagIds.size()];
      for (int i = 0; i < tags.length; i++) {
        tags[i] = (int) parsedTagIds.get(i);
      }

      tagCenters = parseTagArray(dataCam);

      switch (mode) {
        case 0:
          newUpdateNum = dataCam.get("Update").getAsInt();
          Pose3d pose1 = parseJsonPose3d(dataCam.get("Pose1").getAsJsonObject().asMap());
          Pose3d pose2 = parseJsonPose3d(dataCam.get("Pose2").getAsJsonObject().asMap());
          // System.out.println(this.udpPort + " " + pose1);
          // System.out.println(pose2);

          double ambig = dataCam.get("Ambig").getAsDouble();

          curData =
              new WallEyePoseResult(
                  pose1,
                  pose2,
                  tagCenters,
                  timestamp,
                  camIndex,
                  newUpdateNum,
                  tags.length,
                  tags,
                  ambig);
          break;

        case 1:
          newUpdateNum = dataCam.get("Update").getAsInt();

          // [tag index][center index][x/y]

          curData =
              new WallEyeTagResult(
                  tagCenters, timestamp, camIndex, newUpdateNum, tags.length, tags);
          break;
        default:
          break;
      }
    }
    // } catch (Exception e) {
    //   System.err.println(e.toString());
    // }
  }

  private List<List<Double>> parseTagArray(Map<String, JsonElement> data) {
    Type listType = new TypeToken<List<List<Double>>>() {}.getType();
    String tagListString = new Gson().fromJson(data.get("TagCenters"), String.class);

    return new Gson().fromJson(tagListString.replace("\"", ""), listType);
  }

  /**
   * Converts List of JsonElement of tag ids to int tag ids
   *
   * @param tagsList
   * @return List of casted int tag ids
   */
  private int[] getTagsArray(String[] tagsList) {
    int[] tags = new int[tagsList.length];

    for (int i = 0; i < tagsList.length; ++i) {
      tags[i] = Integer.parseInt(tagsList[i]);
    }

    return tags;
  }

  /**
   * @param poseData
   * @return Pose3d
   */
  private Pose3d parseJsonPose3d(Map<String, JsonElement> poseData) {
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
    // WallEyePoseResult result;
    // curUpdateNum = (int) updateSub.get();
    // double[] tempPose1 = pose1Sub.get();
    // double[] tempPose2 = pose2Sub.get();
    // double timestamp = RobotController.getFPGATime() - timestampSub.get();
    // double ambiguity = ambiguitySub.get();
    // long[] tags = tagsSub.get();
    // int[] tagsNew = new int[tags.length];

    // for (int i = 0; i < tags.length; ++i) tagsNew[i] = (int) tags[i];

    // Pose3d pose1 = getPoseFromArray(tempPose1);
    // Pose3d pose2 = getPoseFromArray(tempPose2);

    // result =
    // new WallEyePoseResult(
    // pose1, pose2, timestamp, camIndex, curUpdateNum, tags.length, tagsNew,
    // ambiguity);

    // return result;
    curUpdateNum = curData.getUpdateNum();

    // System.out.println("Called " + curUpdateNum);

    return curData;
  }

  private int[] integerArrayToInt(Integer[] input) {
    int[] tags = new int[input.length];

    for (int i = 0; i < input.length; ++i) {
      tags[i] = input[i];
    }

    return tags;
  }

  private Integer[] parseDataTags(String str) {
    ArrayList<Integer> tags = new ArrayList<Integer>();
    Integer[] tagsArray;
    int tagID = 0;
    int numTags = 0;

    while (tagID != kFinalTagInt) {
      tagID =
          parseDataInt(
              stringToByte(str.substring(kIntByteSize * numTags, kIntByteSize * (numTags + 1))));
      if (tagID == kFinalTagInt) {
        tagsArray = new Integer[tags.size()];
        tags.toArray(tagsArray);
        return tagsArray;
      }
      tags.add(tagID);
      numTags++;
    }

    tagsArray = new Integer[tags.size()];
    tags.toArray(tagsArray);

    return tagsArray;
  }

  private Pose3d parseDataPose(String str) {
    double[] coords = new double[6];

    for (int i = 0; i < 6; ++i) {
      coords[i] =
          parseDataDouble(
              stringToByte(str.substring(kDoubleByteSize * i, kDoubleByteSize * (i + 1))));
    }

    return new Pose3d(
        new Translation3d(coords[0], coords[1], coords[2]),
        new Rotation3d(coords[3], coords[4], coords[5]));
  }

  private double parseDataDouble(byte[] a) {
    if (a == null) return 0;
    return ByteBuffer.wrap(a).getDouble();
  }

  private long parseDataLong(byte[] a) {
    if (a == null) return 0;
    return ByteBuffer.wrap(a).getLong();
  }

  private int parseDataInt(byte[] a) {
    if (a == null) return 0;
    return ByteBuffer.wrap(a).getInt();
  }

  private byte[] stringToByte(String str) {
    return str.getBytes(StandardCharsets.UTF_8);
  }

  private StringBuilder parseDataString(byte[] a) {
    if (a == null) return null;

    StringBuilder ret = new StringBuilder();
    int i = 0;

    while (a[i] != 0) {
      ret.append((char) a[i]);
      i++;
    }

    return ret;
  }

  /**
   * Takes an array of length 6 to turn into a pose
   *
   * @return Pose3d from the given array
   * @throws AssertionError
   */
  private Pose3d getPoseFromArray(double[] arr) {
    assert arr.length == 6;

    return new Pose3d(
        new Translation3d(arr[0], arr[1], arr[2]), new Rotation3d(arr[3], arr[4], arr[5]));
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
