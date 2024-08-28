import cv2
import logging
import numpy as np


class TagProcessor:
    logger = logging.getLogger(__name__)
    MIN_TAG = 1
    MAX_TAG = 16

    # Create a pose estimator
    def __init__(self):
        # Create an aruco detector (finds the tags in images)
        self.aruco_detector = cv2.aruco.ArucoDetector()
        self.aruco_detector.setDictionary(
            cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36H11)
        )

        # Change params to balance speed and accuracy
        aruco_params = cv2.aruco.DetectorParameters()
        aruco_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        aruco_params.cornerRefinementMinAccuracy = 0.1
        aruco_params.cornerRefinementMaxIterations = 30
        self.aruco_detector.setDetectorParameters(aruco_params)

    # Return camera pose
    def get_tags(self, img: np.ndarray, draw: bool):
        if img is None:
            return ([], [])

        corners, ids, _ = self.aruco_detector.detectMarkers(img)

        if ids is None:
            return ([], [])

        mask = (ids >= TagProcessor.MIN_TAG) & (ids <= TagProcessor.MAX_TAG)
        ids = ids[mask]
        corners = np.asarray(corners)[mask]

        if not mask.all():
            TagProcessor.logger.warning(f"Invalid Tags: {ids[~mask]}")

        if len(corners) > 0:
            # Draw lines around tags for ease of seeing (website)
            if draw:
                cv2.aruco.drawDetectedMarkers(img, corners, ids)

        else:
            # No tags
            return ([], [])

        return (ids, corners)
