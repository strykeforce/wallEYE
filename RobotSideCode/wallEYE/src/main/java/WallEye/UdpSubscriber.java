package WallEye;

import edu.wpi.first.wpilibj.Notifier;
import edu.wpi.first.wpilibj.RobotController;
import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.SocketException;

public class UdpSubscriber {
  private byte[] data = new byte[65535];
  private DatagramSocket socket;
  private Notifier udpLoop = new Notifier(this::grabUDPdata);
  private WallEyeCam[] cams;

  public UdpSubscriber(int port, WallEyeCam... cams) {
    this.cams = cams;

    try {
      socket = new DatagramSocket(port);
    } catch (SocketException e) {
      System.err.print("COULD NOT CREATE VISION SOCKET");
    }

    udpLoop.startPeriodic(0.001);
  }

  private void grabUDPdata() {
    DatagramPacket receive = new DatagramPacket(data, data.length);

    try {
      socket.receive(receive);
    } catch (IOException e) {
      System.err.println("COULD NOT RECEIVE UDP DATA: " + e.toString());
    }

    long recievedTime = RobotController.getFPGATime();

    String parsedData = new String(receive.getData(), 0, receive.getLength());

    for (WallEyeCam cam : cams) {
      cam.processUDP(parsedData, recievedTime);
    }

    data = new byte[65535];
  }
}
