package WallEye;

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
import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.SocketException;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.function.DoubleSupplier;

/** A robot side code interface to interact and pull data from an Orange Pi running WallEye */
public class WallEyeCam {
  private DoubleArraySubscriber pose1Sub;
  private DoubleArraySubscriber pose2Sub;
  private DoubleSubscriber timestampSub;
  private DoubleSubscriber ambiguitySub;
  private IntegerArraySubscriber tagsSub;
  private BooleanSubscriber connectSub;
  private int curUpdateNum = 0;
  private IntegerSubscriber updateSub;
  private Transform3d camToCenter;
  private DatagramSocket socket;
  byte[] udpData = new byte[65535];
  String udpNumTargets = "0";
  DoubleSupplier gyro;
  int currentGyroIndex = 0;
  private final int maxGyroResultSize = 100;
  DIOGyroResult[] gyroResults;
  boolean hasTurnedOff;
  Notifier dioLoop = new Notifier(this::grabGyro);
  Notifier udpLoop = new Notifier(this::grabUDPdata);
  int dioPort = -1;
  private int camIndex = -1;
  int udpPort;
  String camName;
  WallEyeResult curData = new WallEyeResult(null, null, 0, 0, 0, 0, null, 0);

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
   * @param udpPort port that recieves the UDP data NEEDS TO MATCH WEB INTERFACE
   * @param dioPort NOT IMPLEMENTED an int that corresponds to the dioport that the strobe is
   *     connected to (-1 to disable it)
   */
  public WallEyeCam(String camName, int camIndex, int udpPort, int dioPort) {
    this.udpPort = udpPort;
    try {
      socket = new DatagramSocket(udpPort);
    } catch (SocketException e) {
      System.err.print("COULD NOT CREATE VISION SOCKET");
    }

    gyroResults = new DIOGyroResult[maxGyroResultSize];
    hasTurnedOff = false;
    this.camIndex = camIndex;
    // this.gyro = gyro;

    if (dioPort > 0) {
      this.dioPort = dioPort;
      dioLoop.startPeriodic(0.01);
    }
    udpLoop.startPeriodic(0.01);
    camToCenter = new Transform3d();
    NetworkTableInstance nt = NetworkTableInstance.getDefault();
    nt.startServer();

    NetworkTable table = nt.getTable(camName);

    double[] def = {2767.0, 2767.0, 2767.0, 2767.0, 2767.0, 2767.0, 2767.0};
    long[] defInt = {-1};

    NetworkTable subTable = table.getSubTable("Result" + camIndex);

    pose1Sub = subTable.getDoubleArrayTopic("Pose1").subscribe(def);
    pose2Sub = subTable.getDoubleArrayTopic("Pose2").subscribe(def);
    timestampSub = subTable.getDoubleTopic("timestamp").subscribe(0.0);
    ambiguitySub = subTable.getDoubleTopic("ambiguity").subscribe(1.0);
    tagsSub = subTable.getIntegerArrayTopic("tags").subscribe(defInt);

    updateSub = table.getIntegerTopic("Update" + camIndex).subscribe(0);
    connectSub = table.getBooleanTopic("Connected" + camIndex).subscribe(false);
    this.camName = camName;
  }

  /** A method that checks the DIO port for an input and upon input will grab gyro and timestamp */
  private void grabGyro() {
    if (!hasTurnedOff) {
      gyroResults[currentGyroIndex] =
          new DIOGyroResult(0.0 /*gyro.getAsDouble()*/, RobotController.getFPGATime());
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

  private void grabUDPdata() {
    DatagramPacket receive = new DatagramPacket(udpData, udpData.length);
    try {
      socket.receive(receive);
      System.out.println(udpData);
    } catch (IOException e) {
      System.err.println("COULD NOT RECEIVE DATA");
    }

    // Data packets are structured as such:
    //  The first element is the cameras name
    //  The second element is an integer that is the camera's update number
    //         (ie how many new packets have been delivered to each camera)
    //  The third element is an integer that represents a mode the camera could be in
    //  The fourth and fifth element is an encoded pose from the camera
    //          each element contains six doubles
    //          X,Y,Z,RX,RY,RZ with RX being the X rotation
    //  The sixth element is a double which is the ambiguity
    //  The seventh element is a double that is a timestamp
    //  The eighth is a list of integers of tag numbers that ends with negative one
    //  THERE ARE NO SPLITTING TOKENS

    String rawDataString = parseDataString(udpData).toString();
    String[] splitData = rawDataString.split(camName);

    // This is a very odd catch, it means that somehow the data when converted to a string had the
    // cameras name twice
    //      ie the doubles when read as a char spell out the tables name (VERY IMPROBABLE [I
    // think?])
    if (splitData.length != 2) {
      return;
    }
    String camData = splitData[1];
    int newUpdateNum = parseDataInt(stringToByte(camData.substring(0, kIntByteSize)));
    int mode = parseDataInt(stringToByte(camData.substring(kIntByteSize, 2 * kIntByteSize)));
    String modeSpecificData = camData.substring(2 * kIntByteSize);

    if (newUpdateNum <= curUpdateNum) return;

    switch (mode) {
      case 0:
        Pose3d pose1 = parseDataPose(modeSpecificData.substring(0, kPoseByteSize));
        Pose3d pose2 = parseDataPose(modeSpecificData.substring(kPoseByteSize, kPoseByteSize * 2));
        double ambig =
            parseDataDouble(
                stringToByte(
                    modeSpecificData.substring(
                        kPoseByteSize * 2, kPoseByteSize * 2 + kDoubleByteSize)));
        double timestamp =
            parseDataDouble(
                stringToByte(
                    modeSpecificData.substring(
                        kPoseByteSize * 2 + kDoubleByteSize,
                        kPoseByteSize * 2 + kDoubleByteSize * 2)));
        Integer[] tags =
            parseDataTags(modeSpecificData.substring(kPoseByteSize * 2 + kDoubleByteSize * 2));
        curData =
            new WallEyeResult(
                pose1,
                pose2,
                timestamp,
                camIndex,
                newUpdateNum,
                tags.length,
                IntegerArrayToInt(tags),
                ambig);
        break;
      case 1:
        break;
      default:
        break;
    }

    // String[] splitData = rawDataString.split("\n");
    // for (String data: splitData) {
    //     String[] camData = data.split("|");
    //     if (camData[0] == camName) {
    //         int updateNum = parseDataInt(stringToByte(camData[1]));
    //         if (updateNum > curUpdateNum) {
    //             curUpdateNum = updateNum;
    //             int mode = parseDataInt(stringToByte(camData[2]));
    //             switch (mode) {
    //                 // This is for pose data
    //                 case 0:
    //                     Pose3d pose1 = parseDataPose(camData[3]);
    //                     Pose3d pose2 = parseDataPose(camData[4]);
    //                     double ambig = parseDataDouble(stringToByte(camData[5]));
    //                     int[] tags = parseDataTags(camData[6]);
    //                     double timestamp = parseDataDouble(stringToByte(camData[7]));

    //                     curData = new WallEyeResult(pose1, pose2, timestamp, camIndex, updateNum,
    // tags.length, tags, ambig);
    //                     break;

    //                 // This is for corner data FIXME
    //                 case 1:

    //                     break;
    //                 default:
    //                     break;
    //             }
    //         }
    //     } else continue;
    // }

    udpData = new byte[65535];
  }

  /**
   * Pulls most recent poses from Network Tables.
   *
   * @return Returns a WallEyeResult
   * @throws AssertionError Happens if network tables feeds a bad value to the pose arrays.
   * @see WallEyeResult
   */
  public WallEyeResult getResults() {
    // WallEyeResult result;
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
    //     new WallEyeResult(
    //         pose1, pose2, timestamp, camIndex, curUpdateNum, tags.length, tagsNew, ambiguity);

    // return result;
    return curData;
  }

  private int[] IntegerArrayToInt(Integer[] input) {
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
    for (int i = 0; i < 6; ++i)
      coords[i] =
          parseDataDouble(
              stringToByte(str.substring(kDoubleByteSize * i, kDoubleByteSize * (i + 1))));
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
    if (index < 0) index += maxGyroResultSize;
    while ((long) gyroResults[index].getTimestamp() > timestamp) {
      index--;
      if (index < 0) index += maxGyroResultSize;
      if (index == currentGyroIndex) return new DIOGyroResult(yaw, timestamp);
    }
    return gyroResults[index];
  }

  /**
   * Getter for the current update number
   *
   * @return Returns the current update number
   */
  public int getUpdateNumber() {
    return (int) updateSub.get();
  }

  /**
   * Check if there is a new update in Network Tables for WallEye
   *
   * @return true if there is an update, false if not
   */
  public boolean hasNewUpdate() {
    return curUpdateNum != (int) updateSub.get();
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
