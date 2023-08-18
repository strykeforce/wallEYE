import cv2
import threading
import logging
import queue

# Inspired by https://stackoverflow.com/questions/54460797/how-to-disable-buffer-in-opencv-camera
class CameraInfo:
    logger = logging.getLogger(__name__)

    def __init__(self, cam, identifier, supportedResolutions, resolution=None, K=None, D=None):
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

    # def read(self):
    #     return (self.lastImage is not None, self.lastImage)

# class BufferlessVideoCapture(cv2.VideoCapture):
#   logger = logging.getLogger(__name__)
#   def __init__(self, name, backend):
#     super().__init__(name, backend)
#     self.q = queue.Queue()
#     t = threading.Thread(target=self._reader)
#     t.daemon = True
#     t.start()

#   # read frames as soon as they are available, keeping only most recent one
#   def _reader(self):
#     while True:
#       ret, frame = super().read()
#       BufferlessVideoCapture.logg
#       if not ret:
#         break
#       if not self.q.empty():
#         try:
#           self.q.get_nowait()   # discard previous (unprocessed) frame
#         except queue.Empty:
#           pass
#       self.q.put(frame)

#   def read(self):
#     return (True, self.q.get())