import cv2
import time
import numpy as np
import json
import os
import shutil
import logging


class Calibration:
    logger = logging.getLogger(__name__)

    # Create a calibration object for the specified camera
    def __init__(
        self,
        delay: float,
        cornerShape: tuple[int, int],
        camPath: str,
        imgPath: str,
        resolution: tuple,
    ):
        self.delay = delay
        self.cornerShape = cornerShape  # (col, row) format
        self.imgPath = imgPath
        self.camPath = camPath
        self.resolution = resolution

        # Create a list for the corner locations for the calibration tag
        self.reference = np.zeros((cornerShape[0] * cornerShape[1], 3), np.float32)
        self.reference[:, :2] = np.mgrid[
            0 : cornerShape[0], 0 : cornerShape[1]
        ].T.reshape(-1, 2)

        # Set values
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

    # Take a frame and process it for calibration
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
        # Convert it to gray and look for calibration board corners
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

        # If there is a board and it has been long enough
        if (
            found
            and time.time() - self.lastImageUsed > self.delay
            and self.isReady(gray, corners)
        ):
            used = True
            self.lastImageUsed = time.time()

            # Refine corner locations (Better calibrations)
            refined = cv2.cornerSubPix(
                gray, corners, refinementWindow, (-1, -1), refinementCriteria
            )

            # Set 3d locations and 2d location for image
            self.objPoints.append(self.reference)
            self.imgPoints.append(refined)

            # Save off time and image
            currTime = time.time_ns()
            pathSaved = os.path.join(self.imgPath, f"{currTime}.png")

            cv2.imwrite(pathSaved, gray)

            Calibration.logger.info(f"Calibration image saved to {pathSaved}")

        # Draw lines for the calibration board
        cv2.drawChessboardCorners(img, self.cornerShape, corners, found)

        if found:
            # cv2.putText(
            #     img,
            #     "Sharp" if self.lastImageSharp else "Blurry",
            #     (0, img.shape[0] - 10),
            #     cv2.FONT_HERSHEY_SIMPLEX,
            #     1,
            #     (255, 0, 0) if self.lastImageSharp else (0, 0, 255),
            #     2,
            # )
            # Text for calibrating the camera
            cv2.putText(
                img,
                "Stable" if self.lastImageStable else "Not stable",
                (0, img.shape[0] - 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 0, 0) if self.lastImageStable else (0, 0, 255),
                2,
            )

        # Keep track of the amount of images taken on the image
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

    # Return all saved calibration images
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
        # Go through each image, grayscale it, find corner loc, refine, and save off 2d and 3d locations
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

    # Generate an openCV calibration and write to a file
    def generateCalibration(self, calFile: str):
        if len(self.objPoints) == 0:
            Calibration.logger.error("Calibration failed: No image data available")
            return False

        # Using the saved off 2d and 3d points, it will return a camera matrix and distortion coeff
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

        # Write to a dictionary
        self.calibrationData = {
            "K": camMtx,
            "dist": distortion,
            "r": rot,
            "t": trans,
            "resolution": self.resolution,
        }

        # Get calibration error and set it
        reprojError = self.getReprojectionError()

        self.calibrationData["reprojError"] = reprojError

        # Write to a calibration file
        with open(calFile, "w") as f:
            json.dump(
                {
                    "camPath": self.camPath,
                    "K": camMtx.tolist(),
                    "dist": distortion.tolist(),
                    "r": np.asarray(rot).tolist(),
                    "t": np.asarray(trans).tolist(),
                    "reproj": reprojError,
                    "resolution": self.resolution,
                },
                f,
            )

        Calibration.logger.info(
            f"Calibration successfully generated and saved to {calFile} with resolution {self.resolution}"
        )

        return ret

    # Check if the current image has a stable board
    def isStable(self, corners: np.ndarray):
        corner1 = corners[0][0]
        corner2 = corners[self.cornerShape[0] * self.cornerShape[1] - 1][0]

        dt = time.time() - self.lastImageUsed

        speed1 = np.linalg.norm(corner1 - self.prevCorner1) / dt
        speed2 = np.linalg.norm(corner2 - self.prevCorner2) / dt

        self.prevCorner1 = corner1
        self.prevCorner2 = corner2

        threshold = self.resolution[0] / 200

        self.lastImageStable = speed1 < threshold and speed2 < threshold

        return self.lastImageStable

    # Not currently used
    # def isSharp(self, img: np.ndarray, threshold: float = 10, cutoff: float = 80):
    #     (h, w) = img.shape

    #     fft = np.fft.fft2(img)
    #     fftShift = np.fft.fftshift(fft)

    #     fftShift[
    #         h // 2 - cutoff : h // 2 + cutoff, w // 2 - cutoff : w // 2 + cutoff
    #     ] = 0

    #     fftShift = np.fft.ifftshift(fftShift)
    #     recon = np.fft.ifft2(fftShift)

    #     self.lastImageSharp = threshold < np.mean(20 * np.log(np.abs(recon)))

    #     return self.lastImageSharp

    # Check if the current image can be use for calibration
    def isReady(
        self, img: np.ndarray, corners: np.ndarray, requiredReadyCounts: int = 10
    ) -> bool:
        if self.isStable(corners):  # Not checking isSharp
            self.readyCounts += 1
        else:
            self.readyCounts = 0

        return requiredReadyCounts <= self.readyCounts

    # calculate error of the calibration
    def getReprojectionError(self) -> float:
        if len(self.objPoints) == 0:
            print("Cannot compute reprojection error: No image data")
            Calibration.logger.error("Cannot compute reprojection error: No image data")
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

    # Load a calibration file 
    def loadCalibration(self, file: str):
        with open(file, "r") as f:
            self.calibrationData = json.load(f)

        self.calibrationData["K"] = np.asarray(self.calibrationData["K"])
        self.calibrationData["dist"] = np.asarray(self.calibrationData["dist"])
        self.calibrationData["r"] = np.asarray(self.calibrationData["r"])
        self.calibrationData["t"] = np.asarray(self.calibrationData["t"])

        Calibration.logger.info(f"Calibration loaded from {file}")

    # Get calibration data from a calibration file
    @staticmethod
    def parseCalibration(file: str):
        Calibration.logger.info(f"Looking for calibration stored at {file}")

        with open(file, "r") as f:
            calibrationData = json.load(f)

        try:
            calibrationData["K"] = np.array(calibrationData["K"])
            calibrationData["dist"] = np.array(calibrationData["dist"])
            calibrationData["r"] = np.array(calibrationData["r"])
            calibrationData["t"] = np.array(calibrationData["t"])
        except:
            Calibration.logger.error(f"Invalid calibration format in {file}")

        return calibrationData

    @staticmethod
    def calibrationPathByCam(camIdentifier, resolution):
        return f"./Calibration/Cam_{camIdentifier.replace(':', '-').replace('.', '-')}_{resolution}CalData.json"
