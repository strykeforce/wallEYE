package WallEye;

public class DIOGyroResult {
    private double gyro;
    private long timestamp;

    protected DIOGyroResult(double gyro, long timestamp) {
        this.gyro = gyro;
        this.timestamp = timestamp;
    }

    protected double getGyro() {
        return gyro;
    }

    protected double getTimestamp() {
        return timestamp;
    }

}
