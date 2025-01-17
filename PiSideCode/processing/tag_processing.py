import cv2
import logging
import numpy as np
import json

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

    def get_tags(self, img: np.ndarray, valid_tags: np.ndarray, draw: bool):
        if img is None:
            return (np.asarray([]), np.asarray([]))

        corners, ids, _ = self.aruco_detector.detectMarkers(img)

        if ids is None:
            return (np.asarray([]), np.asarray([]))

        ids = np.asarray(ids.squeeze())

        if ids.shape == 0:
            return (np.asarray([]), np.asarray([]))

        mask = np.isin(ids, valid_tags)

        if not mask.all():
            TagProcessor.logger.warning(f"Invalid Tags: {ids[~mask]}")

        ids = ids[mask]
        corners = np.asarray(corners)[mask]


        if len(corners.shape) == 5:
            corners = corners[0]


        if len(corners) > 0:
            # Draw lines around tags for ease of seeing (website)
            if draw and len(corners) == len(ids):
                try:
                    cv2.aruco.drawDetectedMarkers(img, corners, ids)
                except cv2.error:
                    TagProcessor.logger.error(f"Could not draw tags: {ids} with corners {corners}")
        else:
            # No tags
            return (np.asarray([]), np.asarray([]))

        return (ids, corners)

    # def get_tag_centers(self, img: np.ndarray, valid_tags: np.ndarray,  draw: bool):
    #     ids, corners = self.get_tags(img, valid_tags, draw)

    #     if corners.shape[0] == 0:
    #         return (np.asarray([]), np.asarray([]))
    #     return (ids, np.mean(corners[:, 0], axis=1))
