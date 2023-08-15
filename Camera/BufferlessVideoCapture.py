import cv2
import threading


# Inspired by https://stackoverflow.com/questions/54460797/how-to-disable-buffer-in-opencv-camera
class BufferlessVideoCapture(cv2.VideoCapture):
    def __init__(self, name):
        super().__init__(name)

        self.lastImage = None
        t = threading.Thread(target=self._reader, daemon=True)
        t.start()

    def _reader(self):
        while True:
            ret, frame = super().read()
            if not ret:
                break

            with self.lock:
                self.lastImage = frame

    def read(self):
        return (self.lastImage is not None, self.lastImage)
