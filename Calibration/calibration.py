import cv2
import time
import numpy as np
import json
import os
import shutil


class Calibration:
    def __init__(
        self,
        delay: float,
        cornerShape: tuple[int, int],
        camPath: str,
        imgPath: str,
    ):
        self.delay = delay
        self.cornerShape = cornerShape # (col, row) format
        self.imgPath = imgPath
        self.camPath = camPath

        self.reference = np.zeros((cornerShape[0] * cornerShape[1], 3), np.float32)
        self.reference[:, :2] = np.mgrid[
            0 : cornerShape[0], 0 : cornerShape[1]
        ].T.reshape(-1, 2)

        self.objPoints = []
        self.imgPoints = []
        self.lastImageUsed = 0
        self.readyCounts = 0

        self.lastImageStable = False
        self.lastImageSharp = False

        self.prevCorner1 = np.array([0, 0])
        self.prevCorner2 = np.array([0, 0])

        if os.path.isdir(self.imgPath):
            shutil.rmtree(self.imgPath)
        os.mkdir(self.imgPath)

    def processFrame(
        self,
        img,
        refinementWindow: tuple[int, int] = (5, 5),
        refinementCriteria: tuple[float, int, float] = (
            cv2.TERM_CRITERIA_EPS + cv2.TermCriteria_COUNT,
            40,
            0.001,
        ),
    ):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        self.imgShape = gray.shape[::-1]
        found, corners = cv2.findChessboardCorners(
            gray,
            self.cornerShape,
            cv2.CALIB_CB_ADAPTIVE_THRESH
            + cv2.CALIB_CB_NORMALIZE_IMAGE
            + cv2.CALIB_CB_FAST_CHECK,
        )

        used = False
        pathSaved = None

        if (
            found
            and time.time() - self.lastImageUsed > self.delay
            and self.isReady(gray, corners)
        ):
            used = True
            self.lastImageUsed = time.time()

            refined = cv2.cornerSubPix(
                gray, corners, refinementWindow, (-1, -1), refinementCriteria
            )

            self.objPoints.append(self.reference)
            self.imgPoints.append(refined)

            currTime = time.time_ns()
            pathSaved = os.path.join(self.imgPath, f"{currTime}.png")

            cv2.imwrite(pathSaved, gray)
            # print(f'Saved to {pathSaved}')

        cv2.drawChessboardCorners(img, self.cornerShape, corners, found)

        if found:
            cv2.putText(
                img,
                "Sharp" if self.lastImageSharp else "Blurry",
                (0, img.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 0, 0) if self.lastImageSharp else (0, 0, 255),
                2,
            )

            cv2.putText(
                img,
                "Stable" if self.lastImageStable else "Not stable",
                (0, img.shape[0] - 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 0, 0) if self.lastImageStable else (0, 0, 255),
                2,
            )

        cv2.putText(
            img,
            f"Imgs taken: {len(self.imgPoints)}",
            (0, img.shape[0] - 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 0, 0) if used else (0, 0, 255),
            2,
        )

        return (img, used, pathSaved)

    def loadSavedImages(
        self,
        imgs: list[str],
        refinementWindow: tuple[int, int] = (5, 5),
        refinementCriteria: tuple[float, int, float] = (
            cv2.TERM_CRITERIA_EPS + cv2.TermCriteria_COUNT,
            40,
            0.001,
        ),
    ):
        for img in imgs:
            saved = cv2.imread(img)
            gray = cv2.cvtColor(saved, cv2.COLOR_BGR2GRAY)
            self.imgShape = gray.shape[::-1]
            found, corners = cv2.findChessboardCorners(
                gray,
                self.cornerShape,
                cv2.CALIB_CB_ADAPTIVE_THRESH
                + cv2.CALIB_CB_NORMALIZE_IMAGE
                + cv2.CALIB_CB_FAST_CHECK,
            )

            if found:
                refined = cv2.cornerSubPix(
                    gray,
                    corners,
                    refinementWindow,
                    (-1, -1),
                    refinementCriteria,
                )

                self.objPoints.append(self.reference)
                self.imgPoints.append(refined)

    def generateCalibration(self, calFile: str):
        if len(self.objPoints) == 0:
            print("Calibration failed: No images available for calibration!")
            return False

        ret, camMtx, distortion, rot, trans = cv2.calibrateCamera(
            self.objPoints,
            self.imgPoints,
            self.imgShape,
            None,
            None,
            flags=cv2.CALIB_RATIONAL_MODEL
            + cv2.CALIB_THIN_PRISM_MODEL
            + cv2.CALIB_TILTED_MODEL,
        ) 

        self.calibrationData = {
            "K": camMtx,
            "dist": distortion,
            "r": rot,
            "t": trans,
        }

        reprojError = self.getReprojectionError()

        self.calibrationData["reprojError"] = reprojError

        with open(calFile, "w") as f:
            json.dump(
                {
                    "camPath": self.camPath,
                    "K": camMtx.tolist(),
                    "dist": distortion.tolist(),
                    "r": np.asarray(rot).tolist(),
                    "t": np.asarray(trans).tolist(),
                    "reproj": reprojError,
                },
                f,
            )

        return ret

    def isStable(self, corners: np.ndarray, threshold: float = 1):
        corner1 = corners[0][0]
        corner2 = corners[self.cornerShape[0] * self.cornerShape[1] - 1][0]

        dt = time.time() - self.lastImageUsed

        speed1 = np.linalg.norm(corner1 - self.prevCorner1) / dt
        speed2 = np.linalg.norm(corner2 - self.prevCorner2) / dt

        self.prevCorner1 = corner1
        self.prevCorner2 = corner2

        self.lastImageStable = speed1 < threshold and speed2 < threshold

        return self.lastImageStable

    def isSharp(self, img: np.ndarray, threshold: float = 16, cutoff: float = 80):
        (h, w) = img.shape

        fft = np.fft.fft2(img)
        fftShift = np.fft.fftshift(fft)

        fftShift[
            h // 2 - cutoff : h // 2 + cutoff, w // 2 - cutoff : w // 2 + cutoff
        ] = 0

        fftShift = np.fft.ifftshift(fftShift)
        recon = np.fft.ifft2(fftShift)

        self.lastImageSharp = threshold < np.mean(20 * np.log(np.abs(recon)))

        return self.lastImageSharp

    def isReady(
        self, img: np.ndarray, corners: np.ndarray, requiredReadyCounts: int = 10
    ) -> bool:
        if self.isStable(corners) and self.isSharp(img):
            self.readyCounts += 1
        else:
            self.readyCounts = 0

        return requiredReadyCounts <= self.readyCounts

    def getReprojectionError(self) -> float:
        if len(self.objPoints) == 0:
            print("Cannot get reprojection error: No data")
            return

        totalError = 0

        for i in range(len(self.objPoints)):
            imgpoints2, _ = cv2.projectPoints(
                self.objPoints[i],
                self.calibrationData["r"][i],
                self.calibrationData["t"][i],
                self.calibrationData["K"],
                self.calibrationData["dist"],
            )
            error = cv2.norm(self.imgPoints[i], imgpoints2, cv2.NORM_L2) / len(
                imgpoints2
            )
            totalError += error

        return totalError / len(self.objPoints)

    def loadCalibration(self, file: str):
        with open(file, "r") as f:
            self.calibrationData = json.load(f)

        self.calibrationData["K"] = np.asarray(self.calibrationData["K"])
        self.calibrationData["dist"] = np.asarray(self.calibrationData["dist"])
        self.calibrationData["r"] = np.asarray(self.calibrationData["r"])
        self.calibrationData["t"] = np.asarray(self.calibrationData["t"])

    @staticmethod
    def parseCalibration(file: str):
        print(f"Looking for calibration stored at {file}")

        with open(file, "r") as f:
            calibrationData = json.load(f)

        calibrationData["K"] = np.array(calibrationData["K"])
        calibrationData["dist"] = np.array(calibrationData["dist"])
        calibrationData["r"] = np.array(calibrationData["r"])
        calibrationData["t"] = np.array(calibrationData["t"])

        return calibrationData

    @staticmethod
    def calibrationPathByCam(camIdentifier):
        return f"./Calibration/Cam_{camIdentifier.replace(':', '-').replace('.', '-')}CalData.json"


if __name__ == "__main__":
    cam = cv2.VideoCapture(0)
    cal = Calibration(1, (7, 7), 0, "calImgs")

    while len(cal.imgPoints) < 15:
        ret, img = cam.read()
        cv2.imshow("Calibrator", cal.processFrame(img)[0])

        if cv2.waitKey(1) == 27:
            break

    cv2.destroyAllWindows()

    cal.generateCalibration("testCal.json")
    cal.loadCalibration("testCal.json")
    print(f"Reprojection error: {cal.getReprojectionError()}")
