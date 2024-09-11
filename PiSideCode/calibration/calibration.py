import cv2
import time
import numpy as np
import json
import os
import shutil
import logging
from enum import Enum
from pathlib import Path
from directory import CONFIG_DIRECTORY
import datetime

class CalibType(Enum):
    CHESSBOARD = "Chessboard"
    CIRCLE_GRID = "Circle Grid"


class Calibrator:
    logger = logging.getLogger(__name__)

    # Create a calibration object for the specified camera
    def __init__(
        self,
        delay: float,
        corner_shape: tuple[int, int],
        cam_path: str,
        img_path: str,
        resolution: tuple,
        calibType: CalibType = CalibType.CIRCLE_GRID,
    ):
        self.delay = delay
        self.corner_shape = corner_shape  # (col, row) format
        self.img_path = img_path
        self.cam_path = cam_path
        self.resolution = resolution
        self.calib_type = calibType

        # Create a list for the corner locations for the calibration tag
        self.reference = np.zeros((corner_shape[0] * corner_shape[1], 3), np.float32)
        if self.calib_type == CalibType.CHESSBOARD:
            self.reference[:, :2] = np.mgrid[
                0 : corner_shape[0], 0 : corner_shape[1]
            ].T.reshape(-1, 2)
        elif self.calib_type == CalibType.CIRCLE_GRID:
            # criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

            blob_params = cv2.SimpleBlobDetector_Params()

            # Change thresholds TODO adjust as necessary
            # blob_params.minThreshold = 8
            # blob_params.maxThreshold = 255

            # # Filter by Area.
            blob_params.filterByArea = True
            blob_params.minArea = 6
            blob_params.maxArea = 250000

            # # Filter by Circularity
            # blob_params.filterByCircularity = True
            # blob_params.minCircularity = 0.1

            # # Filter by Convexity
            # blob_params.filterByConvexity = True
            # blob_params.minConvexity = 0.87

            # # Filter by Inertia
            # blob_params.filterByInertia = True
            # blob_params.minInertiaRatio = 0.01

            self.blob_detector = cv2.SimpleBlobDetector_create(blob_params)

            for i in range(corner_shape[1]):
                self.reference[i * corner_shape[0] : (i + 1) * corner_shape[0]][
                    :, 0
                ] = i
                self.reference[i * corner_shape[0] : (i + 1) * corner_shape[0]][
                    :, 1
                ] = (np.arange(0, corner_shape[0]) * 2 + i % 2)

        # Set values
        self.obj_points: list[np.ndarray] = []
        self.img_points: list[np.ndarray] = []
        self.last_image_used = 0
        self.ready_counts = 0

        self.last_image_stable = False
        self.last_image_sharp = False

        self.prev_corner1 = np.zeros(2)
        self.prev_corner2 = np.zeros(2)

        self.prev_used_corner1 = np.zeros(2)
        self.prev_used_corner2 = np.zeros(2)

        self.overlay = np.zeros((resolution[1], resolution[0], 3), np.uint8)

        if os.path.isdir(self.img_path):
            shutil.rmtree(self.img_path)
        os.mkdir(self.img_path)

    def find_board(
        self,
        img: np.ndarray,
    ) -> tuple[bool, np.ndarray]:
        if self.calib_type == CalibType.CHESSBOARD:
            return cv2.findChessboardCorners(
                img,
                self.corner_shape,
                cv2.CALIB_CB_ADAPTIVE_THRESH
                + cv2.CALIB_CB_NORMALIZE_IMAGE
                + cv2.CALIB_CB_FAST_CHECK,
            )

        elif self.calib_type == CalibType.CIRCLE_GRID:
            keypoints = self.blob_detector.detect(img)
            img = cv2.drawKeypoints(
                img,
                keypoints,
                np.asarray([]),
                (0, 255, 0),
                cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS,
            )
            return cv2.findCirclesGrid(
                img,
                self.corner_shape,
                None,
                flags=cv2.CALIB_CB_ASYMMETRIC_GRID,
            )

    # Take a frame and process it for calibration
    def process_frame(
        self,
        img: np.ndarray,
        refinementWindow: tuple[int, int] = (5, 5),
        refinementCriteria: tuple[float, int, float] = (
            cv2.TERM_CRITERIA_EPS + cv2.TermCriteria_COUNT,
            40,
            0.001,
        ),
        reduction_factor: int=2,
    ) -> tuple[np.ndarray, bool, str]:
        # Convert it to gray and look for calibration board
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        self.img_shape = gray.shape[::-1]

        # reduced = cv2.resize(
        #     gray, (gray.shape[0] // reduction_factor, gray.shape[1] // reduction_factor)
        # )
        # found, _ = self.find_board(reduced)

        # if not found:
        #     return (img, False, None)

        used = False
        path_saved = None

        found, corners = self.find_board(gray)

        # If there is a board and it has been long enough
        if (
            found
            and time.time() - self.last_image_used > self.delay
            and self.is_ready(gray, corners)
        ):
            used = True
            self.update_overlay(corners)
            self.last_image_used = time.time()
            self.prev_used_corner1 = corners[0][0]
            self.prev_used_corner2 = corners[-1][-1]

            # Refine corner locations (Better calibrations)
            refined = cv2.cornerSubPix(
                gray, corners, refinementWindow, (-1, -1), refinementCriteria
            )

            # Set 3d locations and 2d location for image
            self.obj_points.append(self.reference)
            self.img_points.append(refined)

            # Save off time and image
            curr_time = time.time_ns()
            path_saved = os.path.join(self.img_path, f"{curr_time}.png")

            cv2.imwrite(path_saved, gray)

            Calibrator.logger.info(f"Calibration image saved to {path_saved}")

        self.draw_overlay(img)

        # Draw lines for the calibration board
        cv2.drawChessboardCorners(img, self.corner_shape, corners, found)

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
                "Stable" if self.last_image_stable else "Not stable",
                (0, img.shape[0] - 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 0, 0) if self.last_image_stable else (0, 0, 255),
                2,
            )

        # Keep track of the amount of images taken on the image
        cv2.putText(
            img,
            f"Imgs taken: {len(self.img_points)}",
            (0, img.shape[0] - 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 0, 0) if used else (0, 0, 255),
            2,
        )

        return (img, used, path_saved)

    def update_overlay(self, corners: np.ndarray):
        cv2.fillPoly(
            self.overlay,
            [
                np.asarray(
                    [
                        corners[0][0],
                        corners[self.corner_shape[0] - 1][0],
                        corners[-1][0],
                        corners[-(self.corner_shape[0])][0],
                    ],
                    "int32",
                )
            ],
            (
                np.random.randint(0, 255),
                np.random.randint(0, 255),
                np.random.randint(0, 255),
            ),
        )

    def draw_overlay(self, img: np.ndarray, alpha=0.5):
        mask = self.overlay.astype(bool)
        img[mask] = cv2.addWeighted(img, alpha, self.overlay, 1 - alpha, 0)[mask]

    # Return all saved calibration images
    def load_saved_images(
        self,
        imgs: list[str],
        refinementWindow: tuple[int, int] = (5, 5),
        refinementCriteria: tuple[float, int, float] = (
            cv2.TERM_CRITERIA_EPS + cv2.TermCriteria_COUNT,
            40,
            0.001,
        ),
    ):
        # Go through each image, grayscale it, find corner loc, refine, and
        # save off 2d and 3d locations
        for img in imgs:
            saved = cv2.imread(img)
            gray = cv2.cvtColor(saved, cv2.COLOR_BGR2GRAY)
            self.img_shape = gray.shape[::-1]
            found, corners = cv2.findChessboardCorners(
                gray,
                self.corner_shape,
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

                self.obj_points.append(self.reference)
                self.img_points.append(refined)

    # Generate a calibration and write to a file
    def generate_calibration(self, cal_file: str) -> bool:
        if len(self.obj_points) == 0:
            Calibrator.logger.error("Calibration failed: No image data available")
            return False

        # Using the saved off 2d and 3d points, it will return a camera matrix
        # and distortion coeff
        ret, cam_mtx, distortion, rot, trans = cv2.calibrateCamera(
            self.obj_points,
            self.img_points,
            self.img_shape,
            None,
            None,
            # flags=cv2.CALIB_RATIONAL_MODEL
            # + cv2.CALIB_THIN_PRISM_MODEL
            # + cv2.CALIB_TILTED_MODEL,
        )

        # Write to a dictionary
        self.calibration_data = {
            "K": cam_mtx,
            "dist": distortion,
            "r": rot,
            "t": trans,
            "resolution": self.resolution,
        }

        # Get calibration error and set it
        reproj_error = self.get_reprojection_error()

        self.calibration_data["reprojError"] = reproj_error

        Path(os.path.join(CONFIG_DIRECTORY, "calibrations")).mkdir(
            parents=True, exist_ok=True
        )

        # Write to a calibration file
        with open(cal_file, "w") as f:
            json.dump(
                {
                    "camPath": self.cam_path,
                    "K": cam_mtx.tolist(),
                    "dist": distortion.tolist(),
                    "r": np.asarray(rot).tolist(),
                    "t": np.asarray(trans).tolist(),
                    "reproj": reproj_error,
                    "resolution": self.resolution,
                    "timestamp": str(datetime.datetime.now())
                },
                f,
            )

        Calibrator.logger.info(
            f"Calibration successfully generated and saved to {cal_file} with resolution {self.resolution}"
        )

        return ret

    # Check if the current image has a stable board
    def is_stable(self, corners: np.ndarray) -> bool:
        corner1 = corners[0][0]
        corner2 = corners[-1][0]

        dt = time.time() - self.last_image_used

        speed1 = np.linalg.norm(corner1 - self.prev_corner1) / dt
        speed2 = np.linalg.norm(corner2 - self.prev_corner2) / dt

        self.prev_corner1 = corner1
        self.prev_corner2 = corner2

        threshold = self.resolution[0] / 200

        self.last_image_stable = speed1 < threshold and speed2 < threshold

        return self.last_image_stable

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
    def is_ready(
        self, img: np.ndarray, corners: np.ndarray, requiredReadyCounts: int = 6
    ) -> bool:
        threshold = self.resolution[0] / 50
        if (
            np.linalg.norm(self.prev_used_corner1 - corners[0][0]) > threshold
            and np.linalg.norm(self.prev_used_corner2 - corners[-1][-1]) > threshold
            and self.is_stable(corners)
        ):  # Not checking isSharp
            self.ready_counts += 1
        else:
            self.ready_counts = 0

        return requiredReadyCounts <= self.ready_counts

    # calculate error of the calibration
    def get_reprojection_error(self) -> float:
        if len(self.obj_points) == 0:
            Calibrator.logger.error("Cannot compute reprojection error: No image data")
            return

        total_error = 0

        for i in range(len(self.obj_points)):
            imgpoints2, _ = cv2.projectPoints(
                self.obj_points[i],
                self.calibration_data["r"][i],
                self.calibration_data["t"][i],
                self.calibration_data["K"],
                self.calibration_data["dist"],
            )
            error = cv2.norm(self.img_points[i], imgpoints2, cv2.NORM_L2) / len(
                imgpoints2
            )
            total_error += error

        return total_error / len(self.obj_points)

    # Load a calibration file
    def load_calibration(self, file: str):
        with open(file, "r") as f:
            self.calibration_data = json.load(f)

        self.calibration_data["K"] = np.asarray(self.calibration_data["K"])
        self.calibration_data["dist"] = np.asarray(self.calibration_data["dist"])
        self.calibration_data["r"] = np.asarray(self.calibration_data["r"])
        self.calibration_data["t"] = np.asarray(self.calibration_data["t"])

        Calibrator.logger.info(f"Calibration loaded from {file}")

    # Get calibration data from a calibration file
    @staticmethod
    def parse_calibration(file: str) -> dict[str, np.ndarray]:
        Calibrator.logger.info(f"Looking for calibration stored at {file}")

        with open(file, "r") as f:
            calibration_data = json.load(f)

        try:
            calibration_data["K"] = np.asarray(calibration_data["K"])
            calibration_data["dist"] = np.asarray(calibration_data["dist"])
            calibration_data["r"] = np.asarray(calibration_data["r"])
            calibration_data["t"] = np.asarray(calibration_data["t"])
        except Exception:
            Calibrator.logger.error(f"Invalid calibration format in {file}")

        return calibration_data
