package WallEye;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.function.DoubleSupplier;

import edu.wpi.first.math.geometry.Pose3d;
import edu.wpi.first.math.geometry.Rotation3d;
import edu.wpi.first.math.geometry.Transform3d;
import edu.wpi.first.math.geometry.Translation3d;
import edu.wpi.first.networktables.DoubleArraySubscriber;
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
    private DoubleArraySubscriber dsub;
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
        dsub = table.getDoubleArrayTopic("Result" + camIndex).subscribe(def);
        updateSub = table.getIntegerTopic("Update" + camIndex).subscribe(0);
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
     * @see WallEyeResult
    */
    public WallEyeResult getResults() {
        WallEyeResult result;
        curUpdateNum = (int) updateSub.get();
        double[] temp = dsub.get();
        int[] tags = {-1};
        if (temp[7] > 0)
            tags = new int[(int) temp[7]];
                
        for (int j = 0; j < temp[7]; ++j)
            tags[j] = (int) temp[j + 8];

        //(long)temp[6]
        // Array is structed as index 0, 1, 2 are position; 3, 4, 5 are rotation; 6 is a timestamp; 7 is n number of tags; 7 + n are tag ids; 7+n+1 is ambiguity
        if(dioPort > -1 || gyroResults[maxGyroResultSize - 1] == null || temp[6] > gyroResults[currentGyroIndex - 1 >= 0 ? currentGyroIndex - 1 : maxGyroResultSize - 1].getTimestamp())
            result = new WallEyeResult(new Pose3d(new Translation3d(temp[0], temp[1], temp[2]), new Rotation3d(temp[3], temp[4], temp[5])), 
                (double)dsub.getAtomic().timestamp - temp[6], camIndex, curUpdateNum, (int) temp[7], tags, temp[8 + (int) temp[7]]);
        else {
            DIOGyroResult savedStrobe = findGyro((dsub.getAtomic().timestamp + (long)temp[6]), camIndex, temp[5]);

            result = new WallEyeResult(new Pose3d(new Translation3d(temp[0], temp[1], temp[2]), new Rotation3d(0, 0, savedStrobe.getGyro())), 
                savedStrobe.getTimestamp(), camIndex, curUpdateNum, (int) temp[7], tags, temp[8 + (int) temp[7]]);
            }
        return result;
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
     * @param camNum The index number for the camera as shown in the web interface
     * @param translation The Transform3d of camera to the center of the robot when the robot has not turned
    */
    public void setCamToCenter(int camNum, Transform3d translation) {
        camToCenter = translation;
    }

    /**
     * Gets the pose for the center of the robot from a camera pose
     *   
     *
     * @param camNum The index number for the camera as shown in the web interface
     * @param camPose the pose as returned by the camera
     * 
     * @return returns the pose from the center of the robot
    */
    public Pose3d camPoseToCenter(int camNum, Pose3d camPose) {
        return camToCenter != null ? camPose.transformBy(camToCenter) : new Pose3d(new Translation3d(2767.0, 2767.0, 2767.0), new Rotation3d());
    }
}