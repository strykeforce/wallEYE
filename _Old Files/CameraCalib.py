import math

import cv2
import time
import numpy as np
import json
import wpimath.geometry as wpi
from NetworkTableImplementation import NetworkIO

def translation3dToSolvePNP(temp):
    return np.array([-temp.Y(), -temp.Z(), +temp.X()])

def getPose(temp):
    return wpi.Transform3d(wpi.Translation3d(temp["translation"]["x"], temp["translation"]["y"], temp["translation"]["z"]), wpi.Rotation3d(wpi.Quaternion(temp["rotation"]["quaternion"]["W"], temp["rotation"]["quaternion"]["X"], temp["rotation"]["quaternion"]["Y"], temp["rotation"]["quaternion"]["Z"])))

def addCorners(idLoc, cornerLoc):
    return translation3dToSolvePNP(idLoc.translation() + cornerLoc.rotateBy(idLoc.rotation()))


cam = cv2.VideoCapture(1)
ret, img = cam.read()
detect = cv2.aruco.ArucoDetector()
detect.setDictionary(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_16H5))
calibImg = 0
imgPoints = []
objPoints = []
board = (7, 7)
K = 0
D = 0
bh = 7
bw = 7
obj = np.zeros((bh*bw, 3), np.float32)
checkerBoardLength = 0.059
obj[:, :2] = np.mgrid[0:bh, 0:bw].T.reshape(-1, 2) * checkerBoardLength

lastTime = 0
squareLength = .1524
Publisher = NetworkIO(False, 2767)
index = 0

if input("Enter Y for Calib: ") == "Y":
    while calibImg < 50:
        ret, img = cam.read()
        if ret:
            ret, corners = cv2.findChessboardCorners(img, (bw, bh))
            if ret and time.time() - lastTime > 0.8:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), (cv2.TERM_CRITERIA_COUNT, 40, 0.001))
                calibImg += 1
                imgPoints.append(corners)
                objPoints.append(obj)
                lastTime = time.time()
            cv2.drawChessboardCorners(img, (bw, bh), corners, True)

        cv2.imshow("Image", img)
        cv2.waitKey(1)
    ret, K, D, _, _ = cv2.calibrateCamera(objPoints, imgPoints, gray.shape[::-1], None, None)
    print(K)
    print(D)
    data = {"K" : np.asarray(K).tolist(), "D" : np.asarray(D).tolist()}
    json_obj = json.dumps(data, indent= 2)
    with open("CalibData.json", "w") as out:
        out.write(json_obj)
else:
    with open("CalibData.json") as fileIn:
        fin = json.load(fileIn)
        K = np.array(fin["K"])
        D = np.array(fin["D"])

print(K)
print(D)
with open('aprilTagLayout.json', 'r') as f:
    idsTemp = json.load(f)


print(getPose(idsTemp["tags"][5]["pose"]))

while ret:
    print(img.shape)
    (corners, ids, rej) = detect.detectMarkers(img)
    if len(corners) > 0:
        cv2.aruco.drawDetectedMarkers(img, corners, ids)
        objLoc = None
        cornersPNP = None

        for i in ids:
            pose = getPose(idsTemp["tags"][int(i-1)]["pose"])
            c1 = addCorners(pose, wpi.Translation3d(0, squareLength / 2, squareLength / 2))
            c2 = addCorners(pose, wpi.Translation3d(0, -squareLength / 2, squareLength / 2))
            c3 = addCorners(pose, wpi.Translation3d(0, -squareLength / 2, -squareLength / 2))
            c4 = addCorners(pose, wpi.Translation3d(0, squareLength / 2, -squareLength / 2))
            if objLoc is None:
                cornersPNP = corners[0][0]
                objLoc = np.array([c1, c2, c3, c4])
            else:
                cornersPNP = np.concatenate((cornersPNP, corners[1][0]), axis=0)
                objLoc = np.concatenate((objLoc, np.array([c1, c2, c3, c4])))

            ret, rvecs, tvecs = cv2.solvePnP(objLoc, cornersPNP, K, D, useExtrinsicGuess=False, flags=cv2.SOLVEPNP_SQPNP)

            rotMat, _ = cv2.Rodrigues(rvecs)
            transVec = -np.dot(np.transpose(rotMat), tvecs)
            rot3D = wpi.Rotation3d(np.array([+rvecs[2][0], -rvecs[0][0], +rvecs[1][0]]), (rvecs[0][0] ** 2 + rvecs[1][0] ** 2 + rvecs[2][0] ** 2) ** 0.5)

            Pose = wpi.Pose3d(wpi.Translation3d(+transVec[2], -transVec[0], -transVec[1]), rot3D)

            Publisher.publish(index, Publisher.getTime(), Pose)

    if len(rej) > 0:
        cv2.aruco.drawDetectedMarkers(img, rej)
    cv2.imshow("Image", img)
    cv2.waitKey(1)
    ret, img = cam.read()

