import cv2
import json
import logging
import wpimath.geometry as wpi
import numpy as np
import math
# from numba import njit

class PoseProcessor:
    logger = logging.getLogger(__name__)
    CORNER_POSE_ORDER = np.asarray([(-1, -1), (1, -1), (1, 1), (-1, 1)])
    CORNER_DRAW_ORDER = np.asarray([(1, 1, 0), (-1, 1, 0), (1, -1, 0), (-1, -1, 0)])
    BAD_POSE = wpi.Pose3d(wpi.Translation3d(2767, 2767, 2767), wpi.Rotation3d())
    MIN_TAG = 1
    MAX_TAG = 16

    def __init__(self, tag_processor, tag_length):
        # Open tag layout for tag poses
        with open("./processing/april_tag_layout.json", "r") as f:
            self.tag_layout = json.load(f)["tags"]
            PoseProcessor.logger.info("Tag layout loaded")

        self.tag_processor = tag_processor

        self.square_length = tag_length
        self.tag_corner = np.asarray([tag_length, tag_length, 0]) / 2

        self.corner_locs = np.empty((4, 3))

        for i, j in enumerate(PoseProcessor.CORNER_DRAW_ORDER):
            self.corner_locs[i] = self.tag_corner * j

        self.all_corner_poses = {}
        self.tag_transforms = {}

        # Grab tag pose and calcualte each corner location
        for tag_id in range(PoseProcessor.MIN_TAG, PoseProcessor.MAX_TAG + 1):
            pose = PoseProcessor.make_pose_object(self.tag_layout[int(tag_id - 1)]["pose"])

            corner_poses = np.empty((4, 3))

            for corner_index, j in enumerate(PoseProcessor.CORNER_POSE_ORDER):
                corner_poses[corner_index] = PoseProcessor.wpilib_to_cv2_coords(
                    pose
                    + wpi.Transform3d(
                        wpi.Translation3d(0, *(j * self.tag_corner[:2])),
                        wpi.Rotation3d(),
                    )
                )

            self.all_corner_poses[tag_id] = corner_poses

            rot = pose.rotation().rotateBy(wpi.Rotation3d(0, 0, np.pi))
            translation = np.asarray((pose.X(), pose.Y(), pose.Z())).reshape(3, 1)
            rot, _ = cv2.Rodrigues(np.asarray((rot.X(), rot.Y(), rot.Z())).reshape(3, 1))
            self.tag_transforms[tag_id] = PoseProcessor.get_transform(translation, rot)

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
    def wpilib_to_cv2_coords(translation: wpi.Translation3d) -> np.ndarray[float]:
        return np.asarray([-translation.Y(), -translation.Z(), translation.X()])

    # Grab AprilTag pose information
    @staticmethod
    def make_pose_object(pose_dict):
        return wpi.Transform3d(
            wpi.Translation3d(
                pose_dict["translation"]["x"],
                pose_dict["translation"]["y"],
                pose_dict["translation"]["z"],
            ),
            wpi.Rotation3d(
                wpi.Quaternion(
                    pose_dict["rotation"]["quaternion"]["W"],
                    pose_dict["rotation"]["quaternion"]["X"],
                    pose_dict["rotation"]["quaternion"]["Y"],
                    pose_dict["rotation"]["quaternion"]["Z"],
                )
            ).rotateBy(wpi.Rotation3d(0, 0, math.radians(180))),
        )

    # ROT MUST BE A 3x3 ROTATION MATRIX
    @staticmethod
    # @njit
    def get_transform(trans, rot):
        return np.concatenate(
            (np.concatenate((rot, trans), axis=1), np.asarray([[0, 0, 0, 1]])), axis=0
        )

    @staticmethod
    # @njit
    def get_rot_from_transform(transform):
        return transform[:3, :3]

    @staticmethod
    # @njit
    def get_translation_from_transform(transform):
        return transform[:3, 3]

    # Translate corner locations
    # @staticmethod
    # def add_corners(tag_pos: wpi.Pose3d, corner_pos):
    #     return PoseProcessor.wpilib_to_cv2_coords(
    #         tag_pos.translation() + corner_pos.rotateBy(tag_pos.rotation())
    #     )

    def get_trans_rots(
        self, tvecs: np.ndarray, rvecs: np.ndarray, tag_id: int
    ) -> tuple[np.ndarray, np.ndarray]:

        cam_tvecs = tvecs
        cam_rvecs = rvecs

        x, y, z = cam_tvecs
        cam_tvecs = np.asarray([z, -x, -y]).reshape(3, 1)

        x, y, z = cam_rvecs
        cam_rvecs = np.asarray([z, -x, -y]).reshape(3, 1)

        cam_rot_mat, _ = cv2.Rodrigues(cam_rvecs)
        cam_2_tag = PoseProcessor.get_transform(cam_tvecs, cam_rot_mat)
        world_2_tag = self.tag_transforms[tag_id]

        world_2_cam = np.dot(world_2_tag, np.linalg.inv(cam_2_tag))

        trans_vec = PoseProcessor.get_translation_from_transform(world_2_cam)
        rvecs = PoseProcessor.get_rot_from_transform(world_2_cam)
        return (trans_vec, rvecs)

    # Find AprilTags and calculate the camera's pose
    def get_pose(
        self,
        image: np.ndarray,
        K: np.ndarray,
        D: np.ndarray,
        draw: bool,
        valid_tags: np.ndarray
    ) -> tuple[tuple[wpi.Pose3d, wpi.Pose3d], list[int], float]:

        pose1, pose2 = PoseProcessor.BAD_POSE, PoseProcessor.BAD_POSE
        ambig = 2767

        # If an invalid image is given or no calibration return an error
        # pose
        if image is None or K is None or D is None:
            return ((PoseProcessor.BAD_POSE, PoseProcessor.BAD_POSE), [], 2767)

        ids, corners = self.tag_processor.get_tags(image, valid_tags, draw)

        # If you have corners, find pose
        if len(corners) > 0:
            img_tag_corner_poses = None
            img_corner_locs = None

            # Loop through each id
            # Extract corner information
            for tag_count, tag_id in enumerate(ids):
                # Do basic solvePNP
                # Only for drawing axes
                if draw:
                    _, rvec, tvec, _ = cv2.solvePnPGeneric(
                        self.corner_locs,
                        corners[tag_count],
                        K,
                        D,
                        flags=cv2.SOLVEPNP_IPPE_SQUARE,
                    )
                    # Draw axis on the tags
                    cv2.drawFrameAxes(image, K, D, rvec[0], tvec[0], 0.1)

                # Store image and object points
                if img_tag_corner_poses is None:
                    img_corner_locs = corners[tag_count][0]
                    img_tag_corner_poses = self.all_corner_poses[tag_id]
                else:
                    img_corner_locs = np.concatenate(
                        (img_corner_locs, corners[tag_count][0]), axis=0
                    )
                    img_tag_corner_poses = np.concatenate(
                        (img_tag_corner_poses, self.all_corner_poses[tag_id])
                    )

            # Single Tag
            if len(ids) == 1:
                _, rvecs, tvecs, reproj = cv2.solvePnPGeneric(
                    self.corner_locs,
                    corners[0],
                    K,
                    D,
                    flags=cv2.SOLVEPNP_IPPE_SQUARE,
                )

                ambig = reproj[0][0] / reproj[1][0]

                t1, r1 = self.get_trans_rots(
                    tvecs[0].reshape(3, 1), rvecs[0], ids[0]
                )
                t2, r2 = self.get_trans_rots(tvecs[1].reshape(3, 1), rvecs[1], ids[0])
               
                pose1 = wpi.Pose3d(wpi.Translation3d(*t1), wpi.Rotation3d(r1))
                pose2 = wpi.Pose3d(wpi.Translation3d(*t2), wpi.Rotation3d(r2))

            # Multi-tag
            else:
                # Calculate robot pose with 2d and 3d points
                # Sometimes dies:  point_coordinate_variance >=
                # POINT_VARIANCE_THRESHOLD in function 'computeOmega'

                try:
                    _, rvecs, tvecs = cv2.solvePnP(
                        img_tag_corner_poses,
                        img_corner_locs,
                        K,
                        D,
                        flags=cv2.SOLVEPNP_SQPNP,
                    )
                except BaseException as e:
                    PoseProcessor.logger.error(f"solvePnP error?! Details: {e}")
                    pose1 = pose2 = PoseProcessor.BAD_POSE
                    ambig = 2767

                    return ((pose1, pose2), ids, ambig)
                else:
                    # Grab the rotation matrix and find the translation vector
                    rot_mat, _ = cv2.Rodrigues(rvecs)
                    trans_vec = -np.dot(np.transpose(rot_mat), tvecs)
                    trans_vec = np.asarray([trans_vec[2], -trans_vec[0], -trans_vec[1]])

                    rots, _ = cv2.Rodrigues(rot_mat)
                    rot_mat, _ = cv2.Rodrigues(np.asarray([rots[2], -rots[0], rots[1]]))

                    # Convert the rotation matrix to a three rotation system
                    # (yaw, pitch, roll)
                    rot3D = wpi.Rotation3d(rot_mat)
                    pose1 = pose2 = wpi.Pose3d(
                        wpi.Translation3d(*trans_vec),
                        rot3D,
                    )

        return ((pose1, pose2), ids, ambig)
