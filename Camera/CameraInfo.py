import threading


# Inspired by https://stackoverflow.com/questions/54460797/how-to-disable-buffer-in-opencv-camera
class CameraInfo:
    def __init__(
        self, cam, identifier, supportedResolutions, resolution=None, K=None, D=None
    ):
        self.lastImage = None
        # self.lock = threading.Lock()
        t = threading.Thread(target=self._reader, daemon=True)
        t.start()

        self.cam = cam
        self.identifier = identifier
        self.resolution = resolution
        self.supportedResolutions = supportedResolutions

        # Calibration
        self.K = K
        self.D = D

        self.calibrationPath = None

    def _reader(self):
        while True:
            ret, frame = self.cam.read()
            if not ret:
                continue
            # with self.lock:
            self.lastImage = frame
