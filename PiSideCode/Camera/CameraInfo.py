class CameraInfo:
    def __init__(
        self, cam, identifier, supportedResolutions, resolution=None, K=None, D=None
    ):
        self.lastImage = None

        self.cam = cam
        self.identifier = identifier
        self.resolution = resolution
        self.supportedResolutions = supportedResolutions
        self.exposureRange = (0, 100, 1)
        self.brightnessRange = (0, 240, 1)
        self.validFormats = []

        # Calibration
        self.K = K
        self.D = D

        self.calibrationPath = None
