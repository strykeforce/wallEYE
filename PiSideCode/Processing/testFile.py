import numpy as np
import cv2
import time
from Processing import Processor
from NetworkTablePublisher import NetworkIO

IO = NetworkIO(True, 2767, 'WallEYE')
estimator = Processor(.30)
detect = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11))

K = [[960.2619532120356,0,628.6296107134567],[0,971.185318733242,357.0926477839661],[0,0,1]]
D =[0.029518017622772726, -0.1713689123260221, -0.00610110458596447, 0.0055657933086825885,0.11173963217829971]

cam = cv2.VideoCapture(0)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

while True:
    val, img = cam.read()
    imageTime = IO.getTime()
    if img is not None:
        if val:
            poses, tags, ambigs = estimator.imagePose([img], np.asarray([K]), np.asarray([D]), estimator.tagLayout, detect)
            for i in range(len(poses)):
                IO.increaseUpdateNum()
                IO.publish(i, imageTime, poses[i], tags[i], ambigs[i])
        cv2.imshow("img", img)
        cv2.waitKey(1)       