from Processing import Processor
import cv2

processor = Processor(0.15)
frames = processor.getFrames()
print(processor.getNames())
while True:
    for i in range(len(frames)):
        cv2.imshow("Cam" + str(i), frames[i])
        cv2.waitKey(1)
    frames = processor.getFrames()
