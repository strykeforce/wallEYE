class CameraInfo:
    def __init__(
        self, cam, identifier, supportedResolutions, resolution=None, K=None, D=None
    ):
        self.lastImage = None

        self.cam = cam
        self.identifier = identifier
        self.resolution = resolution
        self.supportedResolutions = supportedResolutions

        # Calibration
        self.K = K
        self.D = D

        self.calibrationPath = None