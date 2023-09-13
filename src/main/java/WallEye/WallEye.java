package WallEye;

import java.lang.reflect.Array;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.function.DoubleSupplier;

import edu.wpi.first.math.Pair;
import edu.wpi.first.math.geometry.Pose3d;
import edu.wpi.first.math.geometry.Rotation3d;
import edu.wpi.first.math.geometry.Transform3d;
import edu.wpi.first.math.geometry.Translation3d;
import edu.wpi.first.networktables.DoubleArraySubscriber;
import edu.wpi.first.networktables.IntegerSubscriber;
import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableInstance;
import edu.wpi.first.util.CircularBuffer;
import edu.wpi.first.wpilibj.DigitalInput;
import edu.wpi.first.wpilibj.Notifier;
import edu.wpi.first.wpilibj.RobotController;
import edu.wpi.first.wpilibj2.command.CommandBase;
import WallEye.WallEyeResult;

/**
 * A robot side code interface to interact and pull data from an Orange Pi running WallEye
 */
public class WallEye {
    private ArrayList<DoubleArraySubscriber> dsub = new ArrayList<DoubleArraySubscriber>();
    private int numCameras;
    private int curUpdateNum = 0;
    private IntegerSubscriber updateSub;
    private Transform3d[] camToCenter;
    ArrayList<DigitalInput> dios = new ArrayList<DigitalInput>();
    DoubleSupplier gyro;
    int currentGyroIndex = 0;
    private final int maxGyroResultSize = 100;
    private final int camFPS = 50;
    private final double periodicLoop = 0.001; 
    DIOGyroResult[][] gyroResults;
    boolean[] hasTurnedOff;
    Notifier dioLoop = new Notifier(this::grabGyro);
    HashMap<Integer, Integer> dioHashMap = new HashMap<>();

    /**
     * Creates a WallEye object that can pull pose location and timestamp from Network Tables.
     *   
     *
     * @param  tableName  a string that specifies the table name of the WallEye instance (Look at web interface)
     * @param  numCameras a number that is equal to the number of cameras connected to the PI
     * @param  gyro a DoubleSupplier that supplies the gyro yaw for the robot
     * @param  dioPorts an array that holds all the Ids for the dio ports that the cameras are connected to *EACH CAMERA MUST HAVE A DIO PORT* (to not use DIO yaw reporting put in an empty array)
    */
    public WallEye(String tableName, int numCameras, DoubleSupplier gyro, DigitalInput[] dioPorts)
    {
        gyroResults = new DIOGyroResult[numCameras][maxGyroResultSize];
        hasTurnedOff = new boolean[numCameras];
        if (dioPorts.length > 0)
            dioLoop.startPeriodic(periodicLoop);
        this.gyro = gyro;

        for(int i = 0; i < dioPorts.length; ++i) {
            dios.add(dioPorts[i]);
            dioHashMap.put(dioPorts[i].getChannel(), i);
        }

        camToCenter = new Transform3d[numCameras];
        this.numCameras = numCameras;
        NetworkTableInstance nt = NetworkTableInstance.getDefault();
        nt.startServer();
        NetworkTable table = nt.getTable(tableName);
        double[] def = {2767.0, 2767.0, 2767.0, 2767.0, 2767.0, 2767.0, 2767.0};
        for (int i = 0; i < numCameras; i++) {
            try {
                dsub.add(table.getDoubleArrayTopic("Result" + i).subscribe(def));
            }
            catch (Exception e) {}
        }
        updateSub = table.getIntegerTopic("Update").subscribe(0);
    }

    /**
     * A method that checks the DIO ports for a input and upon input will grab gyro and timestamp
    */
    private void grabGyro() {
        for (DigitalInput dio: dios)
            if (dio.get()) {
                if (!hasTurnedOff[dioHashMap.get(dio.getChannel())]) {
                    gyroResults[dioHashMap.get(dio.getChannel())][currentGyroIndex] = new DIOGyroResult(gyro.getAsDouble(), RobotController.getFPGATime());
                    currentGyroIndex++;
                    currentGyroIndex %= maxGyroResultSize;
                    hasTurnedOff[dioHashMap.get(dio.getChannel())] = true;
                } else {
                    hasTurnedOff[dioHashMap.get(dio.getChannel())] = false;
                }

            }

    }

    /**
     * Getter for the number of Cameras
     *   
     *
     * @return Returns an integer value for the number of cameras attached to the pi as specified by intialization
    */
    public int getNumCameras() {
        return numCameras;
    }

    /**
     * Pulls most recent poses from Network Tables.
     *   Array is structed as index 0, 1, 2 are position; 3, 4, 5 are rotation; 6 is a timestamp; 7 is n number of tags; 7 + n are tag ids; 7+n+1 is ambiguity
     *
     * @return Returns an array of WallEyeResult, with each nth result being the nth camera as shown on the web interface 
     * @see WallEyeResult
    */
    public WallEyeResult[] getResults() {
        ArrayList<WallEyeResult> results = new ArrayList<WallEyeResult>();
        curUpdateNum = (int) updateSub.get();
        for(int i = 0; i < numCameras; ++i) {
            DoubleArraySubscriber sub = dsub.get(i);
            double[] temp = sub.get();
            int[] tags = {-1};
            if (temp[7] > 0)
                tags = new int[(int) temp[7]];
                
            for (int j = 0; j < temp[7]; ++j)
                tags[i] = (int) temp[j + 8];

            //(long)temp[6]
            if(dios.size() == 0 || gyroResults[i][maxGyroResultSize - 1] == null || temp[6] > gyroResults[i][currentGyroIndex - 1 >= 0 ? currentGyroIndex - 1 : maxGyroResultSize - 1].getTimestamp())
                results.add(new WallEyeResult(new Pose3d(new Translation3d(temp[0], temp[1], temp[2]), new Rotation3d(temp[3], temp[4], temp[5])), 
                    (double)sub.getAtomic().timestamp + temp[6], i, curUpdateNum, (int) temp[7], tags, temp[8 + (int) temp[7]] ));
            else {
                DIOGyroResult savedStrobe = findGyro((sub.getAtomic().timestamp + (long)temp[6]), i, temp[5]);

                //System.out.println(savedStrobe.getTimestamp() - ((double)sub.getAtomic().timestamp) + temp[6]);

                results.add(new WallEyeResult(new Pose3d(new Translation3d(temp[0], temp[1], temp[2]), new Rotation3d(0, 0, savedStrobe.getGyro())), 
                    savedStrobe.getTimestamp(), i, curUpdateNum, (int) temp[7], tags, temp[8 + (int) temp[7]] ));
            }
        }
        WallEyeResult[] returnArray = new WallEyeResult[results.size()];
        returnArray = results.toArray(returnArray);
        return returnArray;
    }


    /**
     * A method that will go back until it gets a timestamp from before the network tables reports 
     *  the time
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
        while((long)gyroResults[camIndex][index].getTimestamp() > timestamp) {
            //System.out.println(index);
            index--;
            if (index < 0)
                index += maxGyroResultSize;
            if (index == currentGyroIndex)
                return new DIOGyroResult(yaw, timestamp);
        }
        return gyroResults[camIndex][index];
    }
    // public DIOGyroResult findGyro(long timestamp, int camIndex) {
    //     int max = currentGyroIndex - 1 >= 0 ? currentGyroIndex - 1 : maxGyroResultSize - 1;
    //     int min = currentGyroIndex;
    //     int loops = 0;
    //     int mid = max > min ? (max - min) / 2 : (maxGyroResultSize - min + max) / 2 + min;
    //     mid %= maxGyroResultSize;
        
    //     if (gyroResults[camIndex][maxGyroResultSize-1] == null)
    //         return new DIOGyroResult(0.0, 0);

    //     while ((timestamp - gyroResults[camIndex][mid].getTimestamp() > 1.0/camFPS * 1000000 || timestamp - gyroResults[camIndex][mid].getTimestamp() < 0)&& min != mid && loops < 10) {
    //         loops++;
    //         if (gyroResults[camIndex][mid].getTimestamp() > timestamp)
    //             max = mid;
    //         else 
    //             min = mid;    
    //         mid = max > min ? (max - min) / 2 + min: (maxGyroResultSize - min + max) / 2 + min;
    //         mid %= maxGyroResultSize;
    //     }
    //     return gyroResults[camIndex][mid];
    // }

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
        camToCenter[camNum] = translation;
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
        return camToCenter[camNum] != null ? camPose.transformBy(camToCenter[camNum]) : new Pose3d(new Translation3d(2767.0, 2767.0, 2767.0), new Rotation3d());
    }
}