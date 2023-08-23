package WallEye;

import java.util.ArrayList;
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
    private final int maxGyroResultSize = 200;
    private final double periodicLoop = 0.005; 
    DIOGyroResult[] gyroResults = new DIOGyroResult[maxGyroResultSize];
    Notifier dioLoop = new Notifier(this::grabGyro);

    /**
     * Creates a WallEye object that can pull pose location and timestamp from Network Tables.
     *   
     *
     * @param  tableName  a string that specifies the table name of the WallEye instance (Look at web interface)
     * @param  numCameras a number that is equal to the number of cameras connected to the PI
    */
    public WallEye(String tableName, int numCameras, DoubleSupplier gyro, int[] dioPorts)
    {
        dioLoop.startPeriodic(periodicLoop);
        this.gyro = gyro;
        for(int port: dioPorts)
            dios.add(new DigitalInput(port));

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

    private void grabGyro() {
        for (DigitalInput dio: dios)
            if (dio.get()) {
                gyroResults[currentGyroIndex] = new DIOGyroResult(gyro.getAsDouble(), RobotController.getFPGATime());
                currentGyroIndex++;
                currentGyroIndex %= maxGyroResultSize;
                return;
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
     * Pulls most recent poses from Network Tables. FIXME : WILL HAVE TO SORT OUT NON CHANGED POSES
     *   
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


            if(dios.size() == 0 || gyroResults[maxGyroResultSize - 1] == null || temp[6] > gyroResults[currentGyroIndex - 1 >= 0 ? currentGyroIndex - 1 : maxGyroResultSize - 1].getTimestamp())
                results.add(new WallEyeResult(new Pose3d(new Translation3d(temp[0], temp[1], temp[2]), new Rotation3d(temp[3], temp[4], temp[5])), 
                    temp[6], i, curUpdateNum, (int) temp[7], tags, temp[8 + (int) temp[7]] ));
            else
                results.add(new WallEyeResult(new Pose3d(new Translation3d(temp[0], temp[1], temp[2]), findGyro((long)temp[6])), 
                    temp[6], i, curUpdateNum, (int) temp[7], tags, temp[8 + (int) temp[7]] ));

        }
        WallEyeResult[] returnArray = new WallEyeResult[results.size()];
        returnArray = results.toArray(returnArray);
        return returnArray;
    }


    public Rotation3d findGyro(long timestamp) {
        int max = currentGyroIndex - 1 >= 0 ? currentGyroIndex - 1 : maxGyroResultSize - 1;

        if (gyroResults[maxGyroResultSize - 1] == null || gyroResults[max].getTimestamp() < timestamp)
            return new Rotation3d();

        int min = currentGyroIndex;
        int loops = 0;
        int mid = max > min ? (max - min) / 2 : (maxGyroResultSize - min + max) / 2 + min;
        mid %= maxGyroResultSize;
        while (Math.abs(gyroResults[mid].getTimestamp() - timestamp) > periodicLoop * 1000000 && min != mid && loops < 10) {
            System.out.println(min + " " + mid + " " + max);
            loops++;
            if (gyroResults[mid].getTimestamp() > timestamp)
                max = mid;
            else 
                min = mid;    
            mid = max > min ? (max - min) / 2 + min: (maxGyroResultSize - min + max) / 2 + min;
            mid %= maxGyroResultSize;
        }
        System.out.println(gyroResults[mid].getTimestamp() + " " + timestamp + " " + loops + " " + Math.abs(gyroResults[mid].getTimestamp() - timestamp) + " " + (min != mid));
        return new Rotation3d(0, 0, gyroResults[mid].getGyro());
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