import cv2
import json
import logging
import wpimath.geometry as wpi
import numpy as np
import math


class TagProcessor:
    logger = logging.getLogger(__name__)
    CORNER_POSE_ORDER = np.asarray([(-1, -1), (1, -1), (1, 1), (-1, 1)])
    CORNER_DRAW_ORDER = np.asarray([(1, 1, 0), (-1, 1, 0), (1, -1, 0), (-1, -1, 0)])
    BAD_POSE = wpi.Pose3d(wpi.Translation3d(2767, 2767, 2767), wpi.Rotation3d())
    MIN_TAG = 1
    MAX_TAG = 16

    # Create a pose estimator
    def __init__(self, tag_length: float):
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

    # Set AprilTag side length in meters
    def set_tag_size(self, size: float):
        self.square_length = size

    # Return camera pose
    def get_tags(
        self,
        images: list[np.ndarray],
        resolutions: list[tuple[int, int]],
    ):
        tags = []
        tag_center_normalized = []
        all_corners = []

        # Loop through images
        for img_index, img in enumerate(images):
            tags_visible_img = []
            tag_center_normalized_img = []

            # If an invalid image is given or no calibration return an error
            # pose
            if img is None:
                tags.append([])
                tag_center_normalized.append([])
                continue

            # Find corner locations for all tags in frame
            corners, ids, _ = self.aruco_detector.detectMarkers(
                img
            )  # BEWARE: ids is a 2D array!!!

            mask = (ids >= TagProcessor.MIN_TAG) & (ids <= TagProcessor.MAX_TAG)
            ids = ids[mask]
            corners = np.asarray(corners)[mask]
            resolutions = resolutions.squeeze()[mask.squeeze()]

            if not mask.all():
                TagProcessor.logger.warning(f"Invalid Tags: {ids[~mask]}")

            if len(corners) > 0:
                num = 0

                # Draw lines around tags for ease of seeing (website)
                cv2.aruco.drawDetectedMarkers(img, corners, ids)

                # Loop through each id
                # Extract corner information
                for tag_count, tag_id in enumerate(ids):
                    # Add id information to tagID array
                    tags_visible_img.append(tag_id)
                    tag_center_normalized_img.append(corners[tag_count].mean(axis=0))

                tags.append(tags_visible_img)
                tag_center_normalized.append((tag_center_normalized_img / resolutions[tag_count]).squeeze())
            else:
                # No tags
                tags.append([])
                tag_center_normalized.append([])

        return (tags, tag_center_normalized, corners)
