import cv2
import json
from Processing.utilForProcessor import imagePose
import logging

class Processor:
    logger = logging.getLogger(__name__)

    def __init__(self, tagLength):
        with open ('./Processing/AprilTagLayout.json', 'r') as f:
            self.tagLayout = json.load(f)
            Processor.logger.info("Tag layout loaded")
        self.tagLayout = self.tagLayout["tags"]
        self.arucoDetector = cv2.aruco.ArucoDetector()
        self.arucoDetector.setDictionary(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_16H5))
        self.squareLength = tagLength

    def getPose(self, images, K, D):
        return imagePose(images, K, D, self.tagLayout, self.arucoDetector, self.squareLength)
    