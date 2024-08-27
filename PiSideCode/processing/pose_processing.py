import cv2
import json
import logging
import wpimath.geometry as wpi
import numpy as np
import math


class PoseProcessor:
    logger = logging.getLogger(__name__)
    CORNER_POSE_ORDER = np.asarray([(-1, -1), (1, -1), (1, 1), (-1, 1)])
    CORNER_DRAW_ORDER = np.asarray([(1, 1, 0), (-1, 1, 0), (1, -1, 0), (-1, -1, 0)])
    BAD_POSE = wpi.Pose3d(wpi.Translation3d(2767, 2767, 2767), wpi.Rotation3d())
    MIN_TAG = 1
    MAX_TAG = 16

    # Create a pose estimator
    def __init__(self, tag_length: float):
        # Open tag layout for tag poses
        with open("./processing/april_tag_layout.json", "r") as f:
            self.tag_layout = json.load(f)
            PoseProcessor.logger.info("Tag layout loaded")

        # Save layout
        self.tag_layout = self.tag_layout["tags"]

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

        self.square_length = tag_length
        self.tag_corner = np.asarray([tag_length, tag_length, 0]) / 2

        self.corner_locs = np.empty((4, 3))

        for i, j in enumerate(PoseProcessor.CORNER_DRAW_ORDER):
            self.corner_locs[i] = self.tag_corner * j

    # Return camera pose
    def get_pose(
        self,
        images: list[np.ndarray],
        K: np.ndarray,
        D: np.ndarray,
        resolutions: list[tuple[int, int]],
    ):
        return self.image_pose(images, K, D, self.tag_layout, np.asarray(resolutions))

    # Set AprilTag side length in meters
    def set_tag_size(self, size: float):
        self.square_length = size
        self.tag_corner = np.asarray([size, size, 0]) / 2

        self.corner_locs = np.empty((4, 3))

        for i, j in enumerate(PoseProcessor.CORNER_DRAW_ORDER):
            self.corner_locs[i] = self.tag_corner * j

    # A method that translates the WPILib coordinate system to the openCV
    # coordinate system
    @staticmethod
    def wpilib_to_cv2_coords(translation) -> np.ndarray[float]:
        return np.asarray([-translation.Y(), -translation.Z(), translation.X()])

    # Grab AprilTag pose information
    @staticmethod
    def make_pose_object(temp):
        return wpi.Transform3d(
            wpi.Translation3d(
                temp["translation"]["x"],
                temp["translation"]["y"],
                temp["translation"]["z"],
            ),
            wpi.Rotation3d(
                wpi.Quaternion(
                    temp["rotation"]["quaternion"]["W"],
                    temp["rotation"]["quaternion"]["X"],
                    temp["rotation"]["quaternion"]["Y"],
                    temp["rotation"]["quaternion"]["Z"],
                )
            ).rotateBy(wpi.Rotation3d(0, 0, math.radians(180))),
        )

    # ROT MUST BE A 3x3 ROTATION MATRIX
    @staticmethod
    def get_transform(trans, rot):
        return np.concatenate(
            (np.concatenate((rot, trans), axis=1), np.asarray([[0, 0, 0, 1]])), axis=0
        )

    @staticmethod
    def get_tag_transform(json_id):
        pose = PoseProcessor.make_pose_object(json_id)
        rot = pose.rotation().rotateBy(wpi.Rotation3d(0, 0, math.radians(180)))
        translation = np.asarray([pose.X(), pose.Y(), pose.Z()]).reshape(3, 1)
        rot, _ = cv2.Rodrigues(np.asarray([rot.X(), rot.Y(), rot.Z()]).reshape(3, 1))
        return PoseProcessor.get_transform(translation, rot)

    @staticmethod
    def get_rot_from_transform(transform):
        return transform[:3, :3]

    @staticmethod
    def get_translation_from_transform(transform):
        return transform[:3, 3]

    # Translate corner locations
    @staticmethod
    def add_corners(tag_pos: wpi.Pose3d, corner_pos):
        return PoseProcessor.wpilib_to_cv2_coords(
            tag_pos.translation() + corner_pos.rotateBy(tag_pos.rotation())
        )

    @staticmethod
    def get_trans_rots(
        tvecs: np.ndarray, rvecs: np.ndarray, cur_id: int, layout: list[dict]
    ) -> tuple[np.ndarray, np.ndarray]:

        cam_tvecs = tvecs
        cam_rvecs = rvecs

        x, y, z = cam_tvecs
        cam_tvecs = np.asarray([z, -x, -y]).reshape(3, 1)

        x, y, z = cam_rvecs
        cam_rvecs = np.asarray([z, -x, -y]).reshape(3, 1)

        cam_rot_mat, _ = cv2.Rodrigues(cam_rvecs)
        cam2_tag = PoseProcessor.get_transform(cam_tvecs, cam_rot_mat)
        world2_tag = PoseProcessor.get_tag_transform(layout[cur_id - 1]["pose"])

        world2_cam = np.dot(world2_tag, np.linalg.inv(cam2_tag))

        trans_vec = PoseProcessor.get_translation_from_transform(world2_cam)
        rvecs = PoseProcessor.get_rot_from_transform(world2_cam)
        return (trans_vec, rvecs)

    # Find AprilTags and calculate the camera's pose
    def image_pose(
        self,
        images: list[np.ndarray],
        K: np.ndarray,
        D: np.ndarray,
        layout: list[dict],
        resolutions: np.ndarray,
    ) -> tuple[tuple[wpi.Pose3d, wpi.Pose3d], list[int], list[float], list[np.ndarray]]:
        poses = []
        tags = []
        ambig = []
        tag_center_normalized = []

        # Loop through images
        for img_index, img in enumerate(images):
            pose1 = 0
            pose2 = 0
            tags_visible_img = []
            tag_center_normalized_img = []

            # If an invalid image is given or no calibration return an error
            # pose
            if img is None or K[img_index] is None or D[img_index] is None:
                poses.append((PoseProcessor.BAD_POSE, PoseProcessor.BAD_POSE))
                tags.append([])
                tag_center_normalized.append([])
                ambig.append(2767)
                continue

            # Find corner locations for all tags in frame
            corners, ids, _ = self.aruco_detector.detectMarkers(
                img
            )  # BEWARE: ids is a 2D array!!!

            # If you have corners, find pose
            if len(corners) > 0:
                # Processor.logger.info(corners)
                num = 0

                # Draw lines around tags for ease of seeing (website)
                cv2.aruco.drawDetectedMarkers(img, corners, ids)

                # Filter unwanted tags
                mask = ((ids >= PoseProcessor.MIN_TAG) & (ids <= PoseProcessor.MAX_TAG))
                ids = ids[mask]
                corners = np.asarray(corners)[mask]  # FIXME Unnecessary???
                resolutions = resolutions.squeeze()[mask.squeeze()]
                # FIXME Squeeze corners, ids?

                if not mask.all():
                    PoseProcessor.logger.warning(f"Invalid Tags: {ids[~mask]}")

                all_tag_corner_poses = None
                all_corner_locs = None

                # Loop through each id
                # Extract corner information
                for tag_count, tag_id in enumerate(ids):
                    # Add id information to tagID array
                    tags_visible_img.append(tag_id)
                    tag_center_normalized_img.append(corners[tag_count].mean(axis=0))

                    # Grab tag pose and calcualte each corner location
                    pose = PoseProcessor.make_pose_object(
                        layout[int(tag_id - 1)]["pose"]
                    )

                    corner_poses = np.empty((4, 3))

                    for tag_id, j in enumerate(PoseProcessor.CORNER_POSE_ORDER):
                        corner_poses[tag_id] = PoseProcessor.wpilib_to_cv2_coords(
                            pose
                            + wpi.Transform3d(
                                wpi.Translation3d(0, *(j * self.tag_corner[:2])),
                                wpi.Rotation3d(),
                            )
                        )

                    # Do basic solvePNP
                    # Only for drawing axes
                    _, rvec, tvec, _ = cv2.solvePnPGeneric(
                        self.corner_locs,
                        corners[tag_count],
                        K[img_index],
                        D[img_index],
                        flags=cv2.SOLVEPNP_IPPE_SQUARE,
                    )

                    # Draw axis on the tags
                    cv2.drawFrameAxes(
                        img, K[img_index], D[img_index], rvec[0], tvec[0], 0.1
                    )

                    # Store image and object points
                    if all_tag_corner_poses is None:
                        all_corner_locs = corners[tag_count][0]
                        all_tag_corner_poses = corner_poses
                    else:
                        all_corner_locs = np.concatenate(
                            (all_corner_locs, corners[tag_count][0]), axis=0
                        )
                        all_tag_corner_poses = np.concatenate(
                            (all_tag_corner_poses, corner_poses)
                        )

                if (
                    all_corner_locs is not None
                ):  # Make sure that tag is valid (i >= 0 and i <= 8)
                    # Ambiguity does not matter with 2+ tags
                    if len(ids) > 1:
                        ambig.append(2767)

                # Single Tag
                if len(ids) == 1:
                    _, rvecs, tvecs, reproj = cv2.solvePnPGeneric(
                        self.corner_locs,
                        corners[0],
                        K[img_index],
                        D[img_index],
                        flags=cv2.SOLVEPNP_IPPE_SQUARE,
                    )

                    ambig.append(reproj[0][0] / reproj[1][0])

                    t1, r1 = PoseProcessor.get_trans_rots(
                        tvecs[0].reshape(3, 1), rvecs[0], ids[0], layout
                    )
                    t2, r2 = PoseProcessor.get_trans_rots(
                        tvecs[1].reshape(3, 1), rvecs[1], ids[0], layout
                    )

                    rot3D = wpi.Rotation3d(r1)
                    trans = wpi.Translation3d(t1[0], t1[1], t1[2])

                    pose1 = wpi.Pose3d(trans, rot3D)

                    rot3D = wpi.Rotation3d(r2)
                    trans = wpi.Translation3d(t2[0], t2[1], t2[2])

                    pose2 = wpi.Pose3d(trans, rot3D)

                # Multi-tag
                else:
                    # Calculate robot pose with 2d and 3d points
                    # Sometimes dies:  point_coordinate_variance >=
                    # POINT_VARIANCE_THRESHOLD in function 'computeOmega'

                    try:
                        _, rvecs, tvecs = cv2.solvePnP(
                            all_tag_corner_poses,
                            all_corner_locs,
                            K[img_index],
                            D[img_index],
                            flags=cv2.SOLVEPNP_SQPNP,
                        )
                    except BaseException as e:
                        PoseProcessor.logger.error(f"solvePnP error?! Details: {e}")
                        pose1 = pose2 = PoseProcessor.BAD_POSE
                        tags_visible_img = []
                        ambig = 2767

                        return (poses, tags, ambig)
                    finally:
                        # Grab the rotation matrix and find the translation vector
                        rot_mat, _ = cv2.Rodrigues(rvecs)
                        trans_vec = -np.dot(np.transpose(rot_mat), tvecs)
                        trans_vec = np.asarray(
                            [trans_vec[2], -trans_vec[0], -trans_vec[1]]
                        )

                        rots, _ = cv2.Rodrigues(rot_mat)
                        rot_mat, _ = cv2.Rodrigues(
                            np.asarray([rots[2], -rots[0], rots[1]])
                        )

                        # Convert the rotation matrix to a three rotation system
                        # (yaw, pitch, roll)
                        rot3D = wpi.Rotation3d(rot_mat)
                        pose1 = pose2 = wpi.Pose3d(
                            # Translation between openCV and WPILib
                            wpi.Translation3d(*trans_vec),
                            rot3D,
                        )
                # Append the pose
                poses.append((pose1, pose2))
                tags.append(tags_visible_img)
                tag_center_normalized.append((tag_center_normalized_img / resolutions[tag_count]).squeeze())
                num += 1
            else:
                # No tags
                poses.append((PoseProcessor.BAD_POSE, PoseProcessor.BAD_POSE))
                tags.append([])
                tag_center_normalized.append([])
                ambig.append(2767)

        return (poses, tags, ambig, tag_center_normalized)
