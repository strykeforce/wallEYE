package WallEye;

/**
* A class that holds yaw and timestamp for DIO inputs
*/
public class DIOGyroResult {
    private double gyro = 0;
    private long timestamp = 0;

    /**
    * Hold yaw and timestamp
    * @param gyro a double that represents yaw
    * @param timestamp a timestamp that is from the yaw
    */
    protected DIOGyroResult(double gyro, long timestamp) {
        this.gyro = gyro;
        this.timestamp = timestamp;
    }

    /**
    * Get yaw
    * @return yaw
    */
    protected double getGyro() {
        return gyro;
    }

    /**
    * Get timestamp
    * @return timestamp
    */
    protected double getTimestamp() {
        return timestamp;
    }

}
