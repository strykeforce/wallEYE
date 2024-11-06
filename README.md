# WallEYE
  _See bottom for updated instructions._
  WallEYE is an Apriltag processing software for use in FRC application. This software has a robotside implementation as well as a website interface. This software was made for Orange Pi 5 running Ubuntu (Joshua Riek or Armbian), but it should run fine on a Linux os with V4L2 and a recent Python version (tested with 3.12.3).

  Use `python3.12 init.py` to run. If changes are made to the web interface (frontend portion), `cd web_interface/walleye` and `npm run build` are required to update the site.  

  If using from source, `sudo chmod 4755 /sbin/ifconfig` is required prior to running the first time.

  `walleye.service` is located at `/etc/systemd/system/walleye.service`
  
## Boot Up
  Before connecting a WallEYE installation to a robot network switch, connect the Orange Pi via ethernet directly and turn on the Pi. Using an IP scanner, the PI's IP can be found. From there connect to the website and set a static IP (it is recommended to set a static ip to the format `10.27.67.#` or one that conforms to a team number). Also set a unique name that identifies the WallEYE installation (this is for robot side implementation). Although Calibration may be done on the first bootup it is not required. 
  
## Web Interface
  The WallEYE website has each camera ordered in a specificed manner that is used in other places such as the order of poses returned by the robot side code. This order will only change if cameras and their usb ports are changed. If usb ports are changed it is recommended to download the data from the usb port (calibrations and configuration file) and upload it to the new USB. 
  
## Calibration
  Calibration is done one camera at a time. The calibration script will automatically take a picture once the checkerboard is stable and detected. Calibration will then be ended by the user. Calibrations will automatically be assigned to cameras and calibrations may be uploaded by the user. Pose estimation will work once calibrations have been done for every camera.
  
## Pose Estimation
  Pose estimation is done through cameras detecting Apriltags. It will give the pose of the camera sensor and not the center of the robot. To work for Odometry updates please note that the pose must be transfered to the center of the robot. 
  
## Robot Side Code
  Robot side code starts with making a WallEYE object and passing the unique name that was given to the WallEYE installation. Calling the `getResults()` method on the WallEYE object will return an array of `WallEYEResults` which are from the cameras so camera 1 on the website would be index 0, camera 2 would be index 1, etc. Getting the pose from a WallEYE result is done by calling the `getCameraPose()` which returns a `Pose3d`. As for the timestamp, call the method `getTimeStamp()` and that returns a `double` that is the timestamp of when that result was sent.

## Maintainers
See `STYLE-GUIDE.md`

## Fresh Installation

The instructions below were documented for Ubuntu 24.04.1 (Joshua Riek image)
0. If `install.sh` still works, use that instead (see below).
1. Flash desired image. If balena-etcher keeps failing to create a bootable sd card, try the Raspberry Pi Imager.
2. Install the correct python version or use a `venv`. We are currently using `python3.11`.
3. Get pip if not already installed: `wget https://bootstrap.pypa.io/get-pip.py && python3.11 get-pip.py`
4. Install libraries with `python3.11 -m pip install -r requirements.txt` 
5. Install necessary packages with `sudo apt install v4l-utils net-tools openssh-server`
6. Allow modification of networking without root: `sudo chmod 4755 /usr/sbin/ifconfig`
7. Make `walleye.service` in `/etc/systemd/system` and enable it.
8. Install Node.js and run `npm install react react-dom`. 
9. In `wallEYE/PiSideCode/web_interface/walleye` run `npm install`
10. *Disable Autosuspend!!* and sync clock (if appropriate). 
11. Disable ipv6. This can sometimes cause problems!

OR run `chmod +x install.sh` and `sudo -i -u {USERNAME} [PATH_TO_install.sh_FROM_HOME]` - Tested on Ubuntu 24.04.1 (Joshua Riek and Armbian) AND Disable ipv6. This can sometimes cause problems!

## Distribution

This section documents how to easily distribute wallEYE to OrangePis on the robot.

On your PC, run `git daemon --base-path=. --export-all` in the directory containing the wallEYE folder (after committing)
In another terminal, SSH into the orangepi and run `git pull git://[YOUR_IP]/wallEYE`

Internet connection on orange pis can cause headaches...