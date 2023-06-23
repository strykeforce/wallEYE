import cv2
import numpy as np
import wpimath.geometry as wpi

def translationToSolvePnP(translation):
    return np.asarray([-translation.Y(), -translation.Z(), +translation.X()])

def getPose(temp):
    return wpi.Transform3d(wpi.Translation3d(temp["translation"]["x"], temp["translation"]["y"], temp["translation"]["z"]), wpi.Rotation3d(wpi.Quaternion(temp["rotation"]["quaternion"]["W"], temp["rotation"]["quaternion"]["X"], temp["rotation"]["quaternion"]["Y"], temp["rotation"]["quaternion"]["Z"])))

def addCorners(tagPos, cornerPos):
    return translationToSolvePnP(tagPos.translation() + cornerPos.rotateBy(tagPos.rotation()))

def imagePose(images, K, D, layout, arucoDetector, squareLength):
    poses = []
    
    for img in images:
        corners, ids, rej = arucoDetector.detectMarkers(img)
        if len(corners) > 0:
            num = 0
            cv2.aruco.drawDetectedMarkers(img, corners, ids)
            tagLoc = None
            cornerLoc = None
            for i in ids:
                if i > 8 or i < 0:
                    print(f'BAD TAG ID: {i}')
                    continue
                pose = getPose(layout[int(i - 1)]["pose"])
                c1 = addCorners(pose, wpi.Translation3d(0, squareLength / 2, squareLength / 2))
                c2 = addCorners(pose, wpi.Translation3d(0, -squareLength / 2, squareLength / 2))
                c3 = addCorners(pose, wpi.Translation3d(0, -squareLength / 2, -squareLength / 2))
                c4 = addCorners(pose, wpi.Translation3d(0, squareLength / 2, -squareLength / 2))
                
                if tagLoc is None:
                    cornerLoc = corners[num][0]
                    tagLoc = np.array([c1, c2, c3, c4])
                else:
                    cornerLoc = np.concatenate((cornerLoc, corners[num][0]), axis = 0)
                    tagLoc = np.concatenate((tagLoc, np.asarray([c1, c2, c3, c4])))

                ret, rvecs, tvecs = cv2.solvePnP(tagLoc, cornerLoc, K[num], D[num], useExtrinsicGuess=False,
                                                 flags=cv2.SOLVEPNP_SQPNP)

                rotMat, _ = cv2.Rodrigues(rvecs)
                transVec = -np.dot(np.transpose(rotMat), tvecs)
                rot3D = wpi.Rotation3d(np.array([+rvecs[2][0], -rvecs[0][0], +rvecs[1][0]]),
                                       (rvecs[0][0] ** 2 + rvecs[1][0] ** 2 + rvecs[2][0] ** 2) ** 0.5)

                poses.append(wpi.Pose3d(wpi.Translation3d(+transVec[2], -transVec[0], -transVec[1]), rot3D))    
                num += 1
        else:
            poses.append(wpi.Pose3d(wpi.Translation3d(2767, 2767, 2767), wpi.Rotation3d()))
        

    return poses
