import cv2
import time
from Camera.BootUp import *
from Calibration.calibration import Calibration
import subprocess
import re

class Camera:
    def __init__(self):
        self.cameras = []
        self.index = 0
        self.names = []
        camIndex = 0
        self.by_pathIndexs = []
        self.supportedResolutions = []

        self.K = []
        self.D = []
        # Sometimes there are gaps between the device index.
        # We keep trying max_gaps times.
        max_gaps = 3


        for i in range(2):
            path = f"/dev/v4l/by-path/platform-fc8{0 if i == 0 else 8}0000.usb-usb-0:1:1.0-video-index0"
            cam = cv2.VideoCapture(path)
            self.by_pathIndexs.append(0 if i == 0 else 8)
            if cam.isOpened():

                self.D.append(None)
                self.K.append(None)
                self.supportedResolutions.append(sorted(list(set(map(lambda x: (int(x.split("x")[0]), int(x.split("x")[1])), re.findall("[0-9]+x[0-9]+", subprocess.run(["v4l2-ctl", "-d", path, "--list-formats-ext"], capture_output=True).stdout.decode("utf-8")))))))               
                print(self.supportedResolutions[self.index])
                cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
                self.cameras.append(cam)
                try:
                    config = parseConfig(self.by_pathIndexs[self.index])
                    calib = Calibration.parseCalibration(f"./Calibration/Cam{self.by_pathIndexs[self.index]}CalData.json")
                    self.setCalibration(self.index, calib["K"], calib["dist"])
                except:
                    print(f"Calibration not found for camera {self.index}")
                if config["Resolution"] is not None:
                    self.setResolution(self.index, config["Resolution"])
                    self.setGain(self.index, config["Gain"])
                    self.setExposure(self.index, config["Exposure"])
                #Save configs
                writeConfig(self.by_pathIndexs[self.index], self.getResolution()[self.index], self.getGain()[self.index], self.getExposure()[self.index])

                self.index += 1
        print(self.cameras)



    def setCalibration(self, index, K, D):
        self.K[index] = K
        self.D[index] = D


    def getFrames(self):
        frames = []
        for i in range(self.index):
            _, img = self.cameras[i].read()
            frames.append(img)
        return frames

    def setResolution(self, index, resolution):
        if resolution is None:
            print("Resolution not set")
            return

        print(index, resolution, (self.cameras[index].get(cv2.CAP_PROP_FRAME_WIDTH), self.cameras[index].get(cv2.CAP_PROP_FRAME_HEIGHT) ))
        self.cameras[index].set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.cameras[index].set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

    def setGain(self, index, gain):
        if gain is None:
            print("Gain not set")
            return
        print(gain, self.cameras[index].get(cv2.CAP_PROP_GAIN))
        print(self.cameras[index].set(cv2.CAP_PROP_GAIN, gain))

    def setExposure(self, index, exposure):
        if exposure is None:
            print("Exposure not set")
            return
        print(index, exposure, self.cameras[index].get(cv2.CAP_PROP_EXPOSURE))
        print(self.cameras[index].set(cv2.CAP_PROP_EXPOSURE, exposure))

    def getExposure(self):
        exposure = []
        for cam in self.cameras:
            exposure.append(cam.get(cv2.CAP_PROP_EXPOSURE))
        return exposure

    def getGain(self):
        gain = []
        for cam in self.cameras:
            gain.append(cam.get(cv2.CAP_PROP_GAIN))
        return gain

    def getResolution(self):
        resolution = []
        for cam in self.cameras:
            resolution.append((int(cam.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))))
        return resolution




