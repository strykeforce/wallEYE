import time
import cv2

v = cv2.VideoCapture(0)
t = time.time()
v.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter.fourcc(*"MJPG"))
v.set(cv2.CAP_PROP_FPS, 50)
print(v.get(cv2.CAP_PROP_FPS))
while True:
    t = time.time()

    x = v.read()
    print(time.time() - t)
