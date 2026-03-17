package WallEye;

import edu.wpi.first.wpilibj.Notifier;
import edu.wpi.first.wpilibj.RobotController;

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.SocketException;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

public class UdpSubscriber {
  private byte[] data = new byte[4096];
  private DatagramSocket socket;
  private Notifier udpLoop = new Notifier(this::grabUDPdata);
  private WallEyeCam[] cams;
  private final DatagramPacket receivePacket = new DatagramPacket(data, data.length);

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
    try {
      receivePacket.setLength(data.length); 
      socket.receive(receivePacket);

      long recievedTime = RobotController.getFPGATime();
      
      String parsedData = new String(receivePacket.getData(), 0, receivePacket.getLength());
      if (parsedData != null && !parsedData.isEmpty()) {
        // Parse the string once
        JsonObject allData = JsonParser.parseString(parsedData).getAsJsonObject();
        // Send to each camera
        for (WallEyeCam cam : cams) {
          cam.processUDP(allData, recievedTime);
        }
      }
      
    } catch (IOException e) {
      System.err.println("COULD NOT RECEIVE UDP DATA: " + e.toString());
    }
  }
}
