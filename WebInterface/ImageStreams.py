import cv2
import logging
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.cbook import get_sample_data
import matplotlib.image as mpimg
from matplotlib import cm
import random
import time
logger = logging.getLogger(__name__)

class Buffer:
    outputFrame = b""

    def update(self, img):
        if img is None:
            logger.error("Updated image is None - Skipping")
            return

        self.outputFrame = cv2.imencode(".jpg", img)[1].tobytes()

    def output(self):
        while True:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + self.outputFrame + b"\r\n"
            )

class LivePlotBuffer(Buffer):
    FIELD_DIMS = (16.54, 8.02)
    def __init__(self):
        super(LivePlotBuffer, self).__init__()

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.view_init(elev=35, azim=-80, roll=0)

        self.x, self.y, self.z = [], [], []
        (self.poses2D,) = self.ax.plot3D(self.x, self.y, np.atleast_1d(0), marker=">", markevery=[-1], zorder=10, animated=True)
        (self.poses,) = self.ax.plot3D(self.x, self.y, self.z, marker="o", markevery=[-1], zorder=100, animated=True)

        self.ax.set_xlim(0, LivePlotBuffer.FIELD_DIMS[0])
        self.ax.set_ylim(0, LivePlotBuffer.FIELD_DIMS[1])
        self.ax.set_zlim(0, 2)
        plt.locator_params(axis='z', nbins=2)
        self.ax.set_aspect('equal')
        self.fig.tight_layout()
        self.fig.subplots_adjust(left=-0.26, right=1.21, bottom=-0.08, top=1.08)


        fn = get_sample_data("C:\\Users\\David Shen\\Code\Strykeforce\\wallEYE\\WebInterface\\field.png", asfileobj=False)
        img = mpimg.imread(fn)

        x = np.linspace(0, LivePlotBuffer.FIELD_DIMS[0], img.shape[1])
        y = np.linspace(0, LivePlotBuffer.FIELD_DIMS[1], img.shape[0])
        x, y = np.meshgrid(x, y)
        self.ax.plot_surface(x, y, np.atleast_2d(0), rstride=5, cstride=5, facecolors=img)

        plt.pause(0.1)

        self.bg = self.fig.canvas.copy_from_bbox(self.fig.bbox)
        self.ax.draw_artist(self.poses)
        self.ax.draw_artist(self.poses2D)
        self.fig.canvas.blit(self.fig.bbox)

    def update(self, pose):
        self.fig.canvas.restore_region(self.bg)

        self.x.append(pose[0])
        self.y.append(pose[1])
        self.z.append(pose[2])
        self.x = self.x[-50:]
        self.y = self.y[-50:]
        self.z = self.z[-50:]
        self.poses.set_data(self.x, self.y)
        self.poses.set_3d_properties(self.z)
        self.poses2D.set_data(self.x, self.y)
        self.poses2D.set_3d_properties(np.atleast_1d(0))


        self.ax.draw_artist(self.poses2D)
        self.ax.draw_artist(self.poses)
        self.fig.canvas.blit(self.fig.bbox)
        self.fig.canvas.flush_events()

        plot = np.frombuffer(self.fig.canvas.tostring_rgb(), dtype=np.uint8)
        img  = plot.reshape(self.fig.canvas.get_width_height()[::-1] + (3,))
        self.outputFrame = cv2.imencode(".jpg", img)[1].tobytes()

        


if __name__ == "__main__":
    b = LivePlotBuffer()

    x = 10
    y = 3
    z = 1
    b.update((x, y, z))
    for i in range(3000):
        x += random.randrange(-10, 10) / 10
        y += random.randrange(-10, 10) / 10
        b.update((x, y, z))

        if x > 16 or x < 0 or y < 0 or y > 9:
            x = 10
            y = 3

    plt.show()
