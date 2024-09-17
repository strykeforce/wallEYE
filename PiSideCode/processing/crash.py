import wpimath.geometry as wpi
import numpy as np

r = np.eye(3, 3)
print(r)
print(wpi.Rotation3d(r))