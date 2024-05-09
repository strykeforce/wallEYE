import cv2
import json
import logging
import wpimath.geometry as wpi
import numpy as np
import math


class Processor:
    logger = logging.getLogger(__name__)
    BAD_POSE = wpi.Pose3d(wpi.Translation3d(2767, 2767, 2767), wpi.Rotation3d())
    MIN_TAG = 0
    MAX_TAG = 16

    # Create a pose estimator
    def __init__(self, tag_length: float):
        # Open tag layout for tag poses
        with open("./processing/april_tag_layout.json", "r") as f:
            self.tag_layout = json.load(f)
            Processor.logger.info("Tag layout loaded")

        # Save layout
        self.tag_layout = self.tag_layout["tags"]

        # Create an aruco detector (finds the tags in images)
        self.aruco_detector = cv2.aruco.ArucoDetector()
        self.aruco_detector.setDictionary(
            cv2.aruco.getPredefinedDictionary(
                cv2.aruco.DICT_APRILTAG_36H11
            )  # Old: DICT_APRILTAG_16H5 ---- NEW: DICT_APRILTAG_36H11
        )

        # Change params to balance speed and accuracy
        aruco_params = cv2.aruco.DetectorParameters()
        aruco_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        aruco_params.cornerRefinementMinAccuracy = 0.1
        aruco_params.cornerRefinementMaxIterations = 30
        self.aruco_detector.setDetectorParameters(aruco_params)

        self.square_length = tag_length

    # Return camera pose
    def get_pose(self, images: list[np.ndarray], K: np.ndarray, D: np.ndarray):
        return self.image_pose(images, K, D, self.tag_layout, self.aruco_detector)

    # Set AprilTag side length in meters
    def set_tag_size(self, size: float):
        self.square_length = size

    # A method that translates the WPILib coordinate system to the openCV
    # coordinate system
    @staticmethod
    def translation_to_solve_pnp(translation) -> np.ndarray[float]:
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
        pose = Processor.make_pose_object(json_id)
        rot = pose.rotation().rotateBy(wpi.Rotation3d(0, 0, math.radians(180)))
        translation = np.asarray([pose.X(), pose.Y(), pose.Z()]).reshape(3, 1)
        rot, _ = cv2.Rodrigues(np.asarray([rot.X(), rot.Y(), rot.Z()]).reshape(3, 1))
        return Processor.get_transform(translation, rot)

    @staticmethod
    def get_rot_from_transform(transform):
        return transform[:3, :3]

    @staticmethod
    def get_translation_from_transform(transform):
        return transform[:3, 3]

    # Translate corner locations
    @staticmethod
    def add_corners(tag_pos: wpi.Pose3d, corner_pos):
        return Processor.translation_to_solve_pnp(
            tag_pos.translation() + corner_pos.rotateBy(tag_pos.rotation())
        )

    @staticmethod
    def get_trans_rots(
        tvecs: np.ndarray, rvecs: np.ndarray, cur_id: int, layout: list[dict]
    ) -> tuple[np.ndarray, np.ndarray]:

        cam_tvecs = tvecs

        # ambig.append(reproj[0][0])

        x = cam_tvecs[0]
        y = cam_tvecs[1]
        z = cam_tvecs[2]

        cam_tvecs = np.asarray([z, -x, -y]).reshape(3, 1)

        cam_rvecs = rvecs

        x = cam_rvecs[0]
        y = cam_rvecs[1]
        z = cam_rvecs[2]

        cam_rvecs = np.asarray([z, -x, -y]).reshape(3, 1)

        cam_rot_mat, _ = cv2.Rodrigues(cam_rvecs)
        cam2_tag = Processor.get_transform(cam_tvecs, cam_rot_mat)
        world2_tag = Processor.get_tag_transform(layout[cur_id - 1]["pose"])

        world2_cam = np.dot(world2_tag, np.linalg.inv(cam2_tag))

        trans_vec = Processor.get_translation_from_transform(world2_cam)
        rvecs = Processor.get_rot_from_transform(world2_cam)
        return (trans_vec, rvecs)

    # Find AprilTags and calculate the camera's pose
    def image_pose(
        self,
        images: list[np.ndarray],
        K: np.ndarray,
        D: np.ndarray,
        layout: list[dict],
        aruco_detector: cv2.aruco.ArucoDetector,
    ) -> tuple[tuple[wpi.Pose3d, wpi.Pose3d], list[int], list[float]]:
        poses = []
        tags = []
        ambig = []

        # Loop through images
        for img_index, img in enumerate(images):
            pose1 = 0
            pose2 = 0
            cur_tags = []

            # If an invalid image is given or no calibration return an error
            # pose
            if img is None or K[img_index] is None or D[img_index] is None:
                poses.append((Processor.BAD_POSE, Processor.BAD_POSE))
                tags.append([])
                ambig.append(2767)
                continue

            # Find corner locations for all tags in frame
            corners, ids, rej = aruco_detector.detectMarkers(
                img
            )  # BEWARE: ids is a 2D array!!!

            # If you have corners, find pose
            if len(corners) > 0:
                # Processor.logger.info(corners)
                num = 0

                # Draw lines around tags for ease of seeing (website)
                cv2.aruco.drawDetectedMarkers(img, corners, ids)

                tag_loc = None
                corner_loc = None
                tag_count = 0

                # Loop through each id
                for i in ids:
                    # Filter out invalid ids
                    if i < Processor.MIN_TAG or i > Processor.MAX_TAG:
                        Processor.logger.warning(f"BAD TAG ID: {i}")
                        continue

                    # Add id information to tagID array
                    cur_tags.append(i[0])

                    # Grab tag pose and calcualte each corner location
                    pose = Processor.make_pose_object(layout[int(i - 1)]["pose"])
                    c1 = Processor.translation_to_solve_pnp(
                        pose
                        + wpi.Transform3d(
                            wpi.Translation3d(
                                0, -self.square_length / 2, -self.square_length / 2
                            ),
                            wpi.Rotation3d(),
                        )
                    )
                    c2 = Processor.translation_to_solve_pnp(
                        pose
                        + wpi.Transform3d(
                            wpi.Translation3d(
                                0, self.square_length / 2, -self.square_length / 2
                            ),
                            wpi.Rotation3d(),
                        )
                    )
                    c3 = Processor.translation_to_solve_pnp(
                        pose
                        + wpi.Transform3d(
                            wpi.Translation3d(
                                0, self.square_length / 2, self.square_length / 2
                            ),
                            wpi.Rotation3d(),
                        )
                    )
                    c4 = Processor.translation_to_solve_pnp(
                        pose
                        + wpi.Transform3d(
                            wpi.Translation3d(
                                0, -self.square_length / 2, self.square_length / 2
                            ),
                            wpi.Rotation3d(),
                        )
                    )

                    # Corners as if center of tag is 0,0,0 to draw axis lines
                    tempc1 = np.asarray(
                        [self.square_length / 2, self.square_length / 2, 0]
                    )
                    tempc2 = np.asarray(
                        [-self.square_length / 2, self.square_length / 2, 0]
                    )
                    tempc3 = np.asarray(
                        [self.square_length / 2, -self.square_length / 2, 0]
                    )
                    tempc4 = np.asarray(
                        [-self.square_length / 2, -self.square_length / 2, 0]
                    )

                    # Do basic solvePNP
                    ret, rvec, tvec, reproj = cv2.solvePnPGeneric(
                        np.asarray([tempc2, tempc1, tempc3, tempc4]),
                        corners[tag_count][0],
                        K[img_index],
                        D[img_index],
                        flags=cv2.SOLVEPNP_IPPE_SQUARE,
                    )

                    # Find poses for one tag case
                    if len(ids) == 1:
                        ambig.append(reproj[0][0] / reproj[1][0])

                    # Draw axis on the tags
                    cv2.drawFrameAxes(
                        img, K[img_index], D[img_index], rvec[0], tvec[0], 0.1
                    )

                    # Add 2d location and 3d locations
                    if tag_loc is None:
                        corner_loc = corners[tag_count][0]
                        tag_loc = np.array([c1, c2, c3, c4])
                    else:
                        corner_loc = np.concatenate(
                            (corner_loc, corners[tag_count][0]), axis=0
                        )
                        tag_loc = np.concatenate(
                            (tag_loc, np.asarray([c1, c2, c3, c4]))
                        )
                    tag_count += 1

                if (
                    corner_loc is not None
                ):  # Make sure that tag is valid (i >= 0 and i <= 8)
                    # Ambiguity does not matter with 2+ tags
                    if len(ids) > 1:
                        ambig.append(2767)

                if len(ids) == 1:
                    tempc1 = np.asarray(
                        [self.square_length / 2, self.square_length / 2, 0]
                    )
                    tempc2 = np.asarray(
                        [-self.square_length / 2, self.square_length / 2, 0]
                    )
                    tempc3 = np.asarray(
                        [self.square_length / 2, -self.square_length / 2, 0]
                    )
                    tempc4 = np.asarray(
                        [-self.square_length / 2, -self.square_length / 2, 0]
                    )

                    ret, rvecs, tvecs, reproj = cv2.solvePnPGeneric(
                        np.asarray([tempc2, tempc1, tempc3, tempc4]),
                        corners[0][0],
                        K[img_index],
                        D[img_index],
                        flags=cv2.SOLVEPNP_IPPE_SQUARE,
                    )
                    t1, r1 = Processor.get_trans_rots(
                        tvecs[0].reshape(3, 1), rvecs[0], ids[0][0], layout
                    )
                    t2, r2 = Processor.get_trans_rots(
                        tvecs[1].reshape(3, 1), rvecs[1], ids[0][0], layout
                    )

                    rot3D = wpi.Rotation3d(r1)
                    trans = wpi.Translation3d(t1[0], t1[1], t1[2])

                    pose1 = wpi.Pose3d(trans, rot3D)

                    rot3D = wpi.Rotation3d(r2)
                    trans = wpi.Translation3d(t2[0], t2[1], t2[2])

                    pose2 = wpi.Pose3d(trans, rot3D)

                else:
                    # Calculate robot pose with 2d and 3d points
                    # Sometimes dies:  point_coordinate_variance >=
                    # POINT_VARIANCE_THRESHOLD in function 'computeOmega'

                    try:
                        ret, rvecs, tvecs = cv2.solvePnP(
                            tag_loc,
                            corner_loc,
                            K[img_index],
                            D[img_index],
                            flags=cv2.SOLVEPNP_SQPNP,
                        )
                    except BaseException:
                        Processor.logger.error("solvePnP error?!")
                        poses.append((Processor.BAD_POSE, Processor.BAD_POSE))
                        tags.append([])
                        ambig.append(2767)

                        return (poses, tags, ambig)

                    # ambig.append(reproj[0])

                    # Grab the rotation matrix and find the translation vector
                    rot_mat, _ = cv2.Rodrigues(rvecs)
                    trans_vec = -np.dot(np.transpose(rot_mat), tvecs)
                    trans_vec = np.asarray([trans_vec[2], -trans_vec[0], -trans_vec[1]])

                    rots, _ = cv2.Rodrigues(rot_mat)
                    rot_mat, _ = cv2.Rodrigues(np.asarray([rots[2], -rots[0], rots[1]]))

                    # Convert the rotation matrix to a three rotation system
                    # (yaw, pitch, roll)
                    rot3D = wpi.Rotation3d(rot_mat)
                    pose1 = wpi.Pose3d(
                        # Translation between openCV and WPILib
                        wpi.Translation3d(trans_vec[0], trans_vec[1], trans_vec[2]),
                        rot3D,
                    )
                    pose2 = pose1
                # Append the pose
                poses.append((pose1, pose2))
                tags.append(cur_tags)
                num += 1
            else:
                # If no tags
                poses.append((Processor.BAD_POSE, Processor.BAD_POSE))
                tags.append([])
                ambig.append(2767)

        return (poses, tags, ambig)
