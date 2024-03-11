package WallEye;

import java.time.temporal.Temporal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.function.DoubleSupplier;

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
import edu.wpi.first.wpilibj.DigitalInput;
import edu.wpi.first.wpilibj.Notifier;
import edu.wpi.first.wpilibj.RobotController;

/**
 * A robot side code interface to interact and pull data from an Orange Pi running WallEye
 */
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
    DoubleSupplier gyro;
    int currentGyroIndex = 0;
    private final int maxGyroResultSize = 100;
    DIOGyroResult[] gyroResults;
    boolean hasTurnedOff;
    Notifier dioLoop = new Notifier(this::grabGyro);
    int dioPort = -1;
    private int camIndex = -1;

    /**
     * Creates a WallEye object that can pull pose location and timestamp data from Network Tables.
     *   
     *
     * @param  tableName a string that specifies the table name of the WallEye instance (is set in the web interface)
     * @param  camIndex number to identify the camera as according to webInterface
     * @param  dioPort an int that corresponds to the dioport that the strobe is connected to (-1 to disable it)
     *  
    */
    public WallEyeCam(String tableName, int camIndex, int dioPort)
    {
        gyroResults = new DIOGyroResult[maxGyroResultSize];
        hasTurnedOff = false;
        this.camIndex = camIndex;
        // this.gyro = gyro;
        
        if (dioPort > 0) {
            this.dioPort = dioPort;
            dioLoop.startPeriodic(0.01);
        }

        camToCenter = new Transform3d();
        NetworkTableInstance nt = NetworkTableInstance.getDefault();
        nt.startServer();
        
        NetworkTable table = nt.getTable(tableName);
        
        double[] def = {2767.0, 2767.0, 2767.0, 2767.0, 2767.0, 2767.0, 2767.0};
        long[] defInt = {-1};

        table = table.getSubTable("Result" + camIndex);

        pose1Sub = table.getDoubleArrayTopic("Pose1").subscribe(def);
        pose2Sub = table.getDoubleArrayTopic("Pose2").subscribe(def);
        timestampSub = table.getDoubleTopic("TimeStamp").subscribe(0.0);
        ambiguitySub = table.getDoubleTopic("Ambiguity").subscribe(1.0);
        tagsSub = table.getIntegerArrayTopic("Tags").subscribe(defInt);

        updateSub = table.getIntegerTopic("Update" + camIndex).subscribe(0);
        connectSub = table.getBooleanTopic("Connected" + camIndex).subscribe(false);
    }

    /**
     * A method that checks the DIO port for an input and upon input will grab gyro and timestamp
    */
    private void grabGyro() {
        if (!hasTurnedOff) {
            gyroResults[currentGyroIndex] = new DIOGyroResult(0.0 /*gyro.getAsDouble()*/, RobotController.getFPGATime());
            currentGyroIndex++;
            currentGyroIndex %= maxGyroResultSize;
            hasTurnedOff = true;
        } else {
            hasTurnedOff = false;
        }

    }

    /**
     * TESTME TESTME
     * Check if the camera is still supplying images
     * TESTME TESTME   
     *
     * @return Returns a boolean (True : if and only if the Pi's supplied images are new)
    */
    public boolean isCameraConnected() {
        return connectSub.get();
    }

    /**
     * Getter for the number of Cameras
     *   
     *
     * @return Returns an integer value for the number of cameras attached to the pi as specified by intialization
    */
    public int getCameraIndex() {
        return camIndex;
    }

    /**
     * Pulls most recent poses from Network Tables.
     * 
     * @return Returns an array of WallEyeResult, with each nth result being the nth camera as shown on the web interface 
     * @throws AssertionError Happens if network tables feeds a bad value to the pose arrays.
     * @see WallEyeResult
    */
    public WallEyeResult getResults() {
        WallEyeResult result;
        curUpdateNum = (int) updateSub.get();
        double[] tempPose1 = pose1Sub.get();
        double[] tempPose2 = pose2Sub.get();
        double timestamp = timestampSub.get();
        double ambiguity = ambiguitySub.get();
        long[] tags = tagsSub.get();
        int[] tagsNew = new int[tags.length];

        for (int i = 0; i < tags.length; ++i)
            tagsNew[i] = (int) tags[i];


        Pose3d pose1 = getPoseFromArray(tempPose1);
        Pose3d pose2 = getPoseFromArray(tempPose2);

        result = new WallEyeResult(pose1, pose2, timestamp, camIndex, curUpdateNum, tags.length, tagsNew, ambiguity);
        
        return result;
    }

    /**
     * Takes an array of length 6 to turn into a pose
     * 
     * @return Pose3d from the given array
     * @throws AssertionError
    */
    private Pose3d getPoseFromArray(double[] arr) {
        assert arr.length == 6;
        return new Pose3d(new Translation3d(arr[0], arr[1], arr[2]), new Rotation3d(arr[3], arr[4], arr[5]));
    }

    /**
     * A method that will go back until it gets a timestamp from before the time reported 
     *  by network tables *should return more accurate timestamp measurements*
     * 
     * @param timestamp a long that is the timestamp of the camera that is being searched for
     * @param camIndex an index that corresponds to the camera index
     * @param yaw a yaw that can be returned if it fails
     * 
     * @return Returns a DIOGyroResult with the data of the strobe result
    */
    public DIOGyroResult findGyro(long timestamp, int camIndex, double yaw) {
        int index = currentGyroIndex - 1;
        if (index < 0)
            index += maxGyroResultSize;
        while((long)gyroResults[index].getTimestamp() > timestamp) {
            index--;
            if (index < 0)
                index += maxGyroResultSize;
            if (index == currentGyroIndex)
                return new DIOGyroResult(yaw, timestamp);
        }
        return gyroResults[index];
    }

    /**
     * Getter for the current update number
     *   
     *
     * @return Returns the current update number
    */
    public int getUpdateNumber() {
        return (int) updateSub.get();
    }

    /**
     * Check if there is a new update in Network Tables for WallEye
     *   
     *
     * @return true if there is an update, false if not
    */
    public boolean hasNewUpdate() {
        return curUpdateNum != (int) updateSub.get();
    }

    /**
     * Sets the translation for the camera to the center of the robot
     *   
     *
     * @param translation The Transform3d of camera to the center of the robot when the robot has not turned
    */
    public void setCamToCenter(Transform3d translation) {
        camToCenter = translation;
    }

    /**
     * Gets the pose for the center of the robot from a camera pose
     *   
     *
     * @param camPose the pose as returned by the camera
     * 
     * @return returns the pose from the center of the robot
    */
    public Pose3d camPoseToCenter(Pose3d camPose) {
        return camToCenter != null ? camPose.transformBy(camToCenter) : new Pose3d(new Translation3d(2767.0, 2767.0, 2767.0), new Rotation3d());
    }
}