from calibration import Calibration
import os

calibrator = Calibration(
    0.1,
    (7, 7),
    "Cam_platform-fc880000-usb-usb-0-1-1-0-video-index0",
    "Cam_platform-fc880000-usb-usb-0-1-1-0-video-index0CalImgs",
    (1600, 1200),
)
files = [
    "Cam_platform-fc880000-usb-usb-0-1-1-0-video-index0CalImgs/" + f
    for f in os.listdir("Cam_platform-fc880000-usb-usb-0-1-1-0-video-index0CalImgs")
]
calibrator.load_saved_images(files)
calibrator.generate_calibration(
    "Cam_platform-fc880000-usb-usb-0-1-1-0-video-index0_(1600, 1200)CalData"
)
