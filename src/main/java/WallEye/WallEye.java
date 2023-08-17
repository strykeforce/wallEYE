package WallEye;

import java.util.ArrayList;

import edu.wpi.first.math.geometry.Pose3d;
import edu.wpi.first.math.geometry.Rotation3d;
import edu.wpi.first.math.geometry.Translation3d;
import edu.wpi.first.networktables.DoubleArraySubscriber;
import edu.wpi.first.networktables.IntegerSubscriber;
import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableInstance;
import WallEye.WallEyeResult;

/**
 * A robot side code interface to interact and pull data from an Orange Pi running WallEye
 */
public class WallEye {
    private ArrayList<DoubleArraySubscriber> dsub = new ArrayList<DoubleArraySubscriber>();
    private int numCameras;
    private int curUpdateNum = 0;
    private IntegerSubscriber updateSub;

    /**
     * Creates a WallEye object that can pull pose location and timestamp from Network Tables.
     *   
     *
     * @param  tableName  a string that specifies the table name of the WallEye instance (Look at web interface)
     * @param  numCameras a number that is equal to the number of cameras connected to the PI
    */
    public WallEye(String tableName, int numCameras)
    {
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
            int[] tags = new int[(int) temp[7]];
            for (int j = 0; j < temp[7]; ++j)
                tags[i] = (int) temp[j + 8];

            results.add(new WallEyeResult(new Pose3d(new Translation3d(temp[0], temp[1], temp[2]), new Rotation3d(temp[3], temp[4], temp[5])), 
                temp[6], i, curUpdateNum, (int) temp[7], tags));

        }
        WallEyeResult[] returnArray = new WallEyeResult[results.size()];
        returnArray = results.toArray(returnArray);
        return returnArray;
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
        return curUpdateNum < (int) updateSub.get();
    }
}