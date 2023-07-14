# WallEYE
  WallEYE is an Apriltag processing software for use in FRC application. This software has a robotside implementation as well as a website interface. This software was made for Orange Pi 5 running Ubuntu, but it should run fine on a linux os with V4L2 and a recent Python version (tested with 3.10).

  Use `python3 init.py` to run. If changes are made to the web interface (frontend portion), `cd WebInterface/walleye` and `npm run build` are required to update the site.  
  
# Boot Up
  Before connecting a WallEYE installation to a robot network switch, connect the Orange Pi via ethernet directly and turn on the Pi. Upon turning on the Pi connect to the local website at the ip ---.---.--- FIX ME. Upon connecting it is recommended to set a static ip to the format `10.27.67.#` or one that conforms to a team number. Also set a unique name that identifies the WallEYE installation. Although Calibration may be done on the first bootup it is not required. 
  
# Web Interface
  The WallEYE website has each camera ordered in a specificed manner that is used in other places such as the order of poses returned by the robot side code. This order will only change if cameras and their usb ports are changed. If usb ports are changed it is recommended to download the data from the usb port (calibrations and configuration file) and upload it to the new port number. 
  
# Calibration
  Calibration is done one camera at a time. The calibration script will automatically take a picture once the checkerboard is stable and detected. Calibration will then be ended once ended by the user. Calibrations will automatically be assigned to cameras and calibrations may be uploaded by the user. Pose estimation will work once calibrations have been done for every camera.
  
# Pose Estimation
  Pose estimation is done through cameras detecting Apriltags. It will give the pose of the camera sensor and not the center of the robot. To work for Odometry updates please note that the pose must be transfered to the center of the robot.
  
# Robot Side Code
  Robot side code starts with making a WallEYE object and passing the unique name that was given to the WallEYE installation. Calling the `getResults()` method on the WallEYE object will return an array of `WallEYEResults` which are from the cameras so camera 1 on the website would be index 0, camera 2 would be index 1, etc. Getting the pose from a WallEYE result is done by calling the `getCameraPose()` which returns a `Pose3d`. As for the timestamp, call the method `getTimeStamp()` and that returns a `double` that is the timestamp of when that result was sent.
