import cv2
import json
import logging
import wpimath.geometry as wpi
import numpy as np
import time


class Processor:
    logger = logging.getLogger(__name__)
    BAD_POSE = wpi.Pose3d(wpi.Translation3d(2767, 2767, 2767), wpi.Rotation3d())

    def __init__(self, tagLength):
        with open("./Processing/AprilTagLayout.json", "r") as f:
            self.tagLayout = json.load(f)
            Processor.logger.info("Tag layout loaded")
        self.tagLayout = self.tagLayout["tags"]
        self.arucoDetector = cv2.aruco.ArucoDetector()
        self.arucoDetector.setDictionary(
            cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_16H5)
        )
        arucoParams = cv2.aruco.DetectorParameters()
        arucoParams.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        arucoParams.cornerRefinementMinAccuracy = 0.1
        arucoParams.cornerRefinementMaxIterations = 30
        self.arucoDetector.setDetectorParameters(arucoParams)

        self.squareLength = tagLength

    def getPose(self, images, K, D):
        return self.imagePose(images, K, D, self.tagLayout, self.arucoDetector)

    def setTagSize(self, size):
        self.squareLength = size

    @staticmethod
    def translationToSolvePnP(translation):
        return np.asarray([-translation.Y(), -translation.Z(), translation.X()])

    @staticmethod
    def makePoseObject(temp):
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
            ),
        )

    @staticmethod
    def addCorners(tagPos, cornerPos):
        return Processor.translationToSolvePnP(
            tagPos.translation() + cornerPos.rotateBy(tagPos.rotation())
        )

    def imagePose(self, images, K, D, layout, arucoDetector):
        poses = []
        tags = []
        ambig = []
        for imgIndex, img in enumerate(images):
            curTags = [0]

            if img is None or K[imgIndex] is None or D[imgIndex] is None:
                poses.append(Processor.BAD_POSE)
                tags.append([])
                ambig.append(2767)
                continue
            corners, ids, rej = arucoDetector.detectMarkers(
                img
            )  # BEWARE: ids is a 2D array!!!
            
            if len(corners) > 0:
                # Processor.logger.info(corners)
                num = 0
                
                cv2.aruco.drawDetectedMarkers(img, corners, ids)
                
                tagLoc = None
                cornerLoc = None
                tagCount = 0
                for i in ids:
                    if i > 8 or i <= 0:
                        Processor.logger.warning(f"BAD TAG ID: {i}")
                        continue
                    curTags[0] += 1
                    curTags.append(i[0])
                    pose = Processor.makePoseObject(layout[int(i - 1)]["pose"])
                    c1 = Processor.translationToSolvePnP(
                        pose
                        + wpi.Transform3d(
                            wpi.Translation3d(
                                0, -self.squareLength / 2, -self.squareLength / 2
                            ),
                            wpi.Rotation3d(),
                        )
                    )
                    c2 = Processor.translationToSolvePnP(
                        pose
                        + wpi.Transform3d(
                            wpi.Translation3d(
                                0, self.squareLength / 2, -self.squareLength / 2
                            ),
                            wpi.Rotation3d(),
                        )
                    )
                    c3 = Processor.translationToSolvePnP(
                        pose
                        + wpi.Transform3d(
                            wpi.Translation3d(
                                0, self.squareLength / 2, self.squareLength / 2
                            ),
                            wpi.Rotation3d(),
                        )
                    )
                    c4 = Processor.translationToSolvePnP(
                        pose
                        + wpi.Transform3d(
                            wpi.Translation3d(
                                0, -self.squareLength / 2, self.squareLength / 2
                            ),
                            wpi.Rotation3d(),
                        )
                    )
                    tempc1 = np.asarray(
                        [self.squareLength / 2, self.squareLength / 2, 0]
                    )
                    tempc2 = np.asarray(
                        [-self.squareLength / 2, self.squareLength / 2, 0]
                    )
                    tempc3 = np.asarray(
                        [self.squareLength / 2, -self.squareLength / 2, 0]
                    )
                    tempc4 = np.asarray(
                        [-self.squareLength / 2, -self.squareLength / 2, 0]
                    )

                    ret, rvec, tvec, reproj = cv2.solvePnPGeneric(
                        np.asarray([tempc2, tempc1, tempc3, tempc4]),
                        corners[tagCount][0],
                        K[imgIndex],
                        D[imgIndex],
                        flags=cv2.SOLVEPNP_IPPE_SQUARE,
                    )
                  
                    
                    if len(ids) == 1:
                        ambig.append(reproj[0][0] / reproj[1][0])

                    cv2.drawFrameAxes(
                        img, K[imgIndex], D[imgIndex], rvec[0], tvec[0], 0.1
                    )

                    if tagLoc is None:
                        cornerLoc = corners[tagCount][0]
                        tagLoc = np.array([c1, c2, c3, c4])
                    else:
                        cornerLoc = np.concatenate(
                            (cornerLoc, corners[tagCount][0]), axis=0
                        )
                        tagLoc = np.concatenate((tagLoc, np.asarray([c1, c2, c3, c4])))
                    tagCount += 1

                if (
                    cornerLoc is not None
                ):  # Make sure that tag is valid (i >= 0 and i <= 8)
                    if len(ids) > 1:
                        ambig.append(2767)
                    ret, rvecs, tvecs = cv2.solvePnP(
                        tagLoc,
                        cornerLoc,
                        K[imgIndex],
                        D[imgIndex],
                        flags=cv2.SOLVEPNP_SQPNP,
                    )

                    rotMat, _ = cv2.Rodrigues(rvecs)
                    transVec = -np.dot(np.transpose(rotMat), tvecs)
                    rot3D = wpi.Rotation3d(
                        np.array([rvecs[2][0], -rvecs[0][0], +rvecs[1][0]]),
                        (rvecs[0][0] ** 2 + rvecs[1][0] ** 2 + rvecs[2][0] ** 2) ** 0.5,
                    )

                    poses.append(
                        wpi.Pose3d(
                            wpi.Translation3d(transVec[2], -transVec[0], -transVec[1]),
                            rot3D,
                        )
                    )
                    tags.append(curTags)
                    num += 1
            else:
                poses.append(Processor.BAD_POSE)
                tags.append([])
                ambig.append(2767)
            

        return (poses, tags, ambig)
