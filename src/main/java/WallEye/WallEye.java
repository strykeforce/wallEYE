package WallEye;

import java.util.ArrayList;

import edu.wpi.first.math.geometry.Pose3d;
import edu.wpi.first.math.geometry.Rotation3d;
import edu.wpi.first.math.geometry.Translation3d;
import edu.wpi.first.networktables.DoubleArraySubscriber;
import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableInstance;
import WallEye.WallEyeResult;

public class WallEye {
    ArrayList<DoubleArraySubscriber> dsub;
    public WallEye(String tableName)
    {
        NetworkTableInstance nt = NetworkTableInstance.getDefault();
        nt.startServer();
        NetworkTable table = nt.getTable(tableName);
        double[] def = {2767.0, 2767.0, 2767.0, 2767.0, 2767.0, 2767.0, 2767.0};
        for (int i = 0; true; i++) {
            try {
                dsub.add(table.getDoubleArrayTopic("Result" + i).subscribe(def));
            }
            catch (Exception e) {}
        }
    }

    public WallEyeResult[] getResults() {
        ArrayList<WallEyeResult> results = new ArrayList<WallEyeResult>();
        for(DoubleArraySubscriber sub: dsub) {
            double[] temp = sub.get();
            results.add(new WallEyeResult(new Pose3d(new Translation3d(temp[0], temp[1], temp[2]), new Rotation3d(temp[3], temp[4], temp[5])), temp[6]));
        }
        WallEyeResult[] returnArray = new WallEyeResult[results.size()];
        returnArray = results.toArray(returnArray);
        return returnArray;
    }
}