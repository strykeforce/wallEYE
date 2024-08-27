from numba import njit
import numba as nb
import numpy as np

FAST_MATH = True


@njit(
    nb.types.Array(nb.float64, 2, "C")(nb.types.Array(nb.float64, 1, "C")),
    fastmath=FAST_MATH,
)
def euler_to_matrix(euler):
    # assert euler.shape == (3,)

    sin_alpha, sin_beta, sin_gamma = np.sin(euler)
    cos_alpha, cos_beta, cos_gamma = np.cos(euler)

    return np.asarray(
        [
            [
                cos_beta * cos_gamma,
                sin_alpha * sin_beta * cos_gamma - sin_gamma * cos_alpha,
                sin_beta * cos_alpha * cos_gamma + sin_alpha * sin_gamma,
            ],
            [
                sin_gamma * cos_beta,
                sin_alpha * sin_beta * sin_gamma + cos_alpha * cos_gamma,
                sin_beta * sin_gamma * cos_alpha - sin_alpha * cos_gamma,
            ],
            [-sin_beta, sin_alpha * cos_beta, cos_alpha * cos_beta],
        ],
    )


@njit(
    nb.types.Array(nb.float64, 2, "C")(nb.types.Array(nb.float64, 1, "C")),
    fastmath=FAST_MATH,
)
def quaterion_to_matrix(q):
    # assert q.shape == (4,)

    w, x, y, z = q

    rotation_matrix = np.asarray(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ],
    )

    return rotation_matrix


# ROT MUST BE A 3x3 ROTATION MATRIX
@njit(
    nb.types.Array(nb.float64, 2, "C")(
        nb.types.Array(nb.float64, 1, "C"), nb.types.Array(nb.float64, 2, "C")
    ),
    fastmath=FAST_MATH,
)
def make_transform(trans, rot):
    # assert trans.shape == (3, 1) and rot.shape == (3, 3)

    return np.concatenate(
        (
            np.concatenate((rot, np.atleast_2d(trans).T), axis=1),
            np.asarray([[0, 0, 0, 1]]),
        ),
        axis=0,
    )


@njit(
    nb.types.Array(nb.float64, 2, "C")(nb.types.Array(nb.float64, 1, "C")),
    fastmath=FAST_MATH,
)
def make_rotation_transform(euler):
    # assert euler.shape == (3,)

    return make_transform(np.zeros(3), euler_to_matrix(euler))


@njit(
    nb.types.Array(nb.float64, 2, "C")(nb.types.Array(nb.float64, 1, "C")),
    fastmath=FAST_MATH,
)
def make_translation_transform(translation):
    # assert translation.shape == (3,)

    return make_transform(translation, np.eye(3, 3))


@njit(
    nb.types.Array(nb.float64, 2, "A")(nb.types.Array(nb.float64, 2, "C")),
    fastmath=FAST_MATH,
)
def get_rotation(transform):
    # assert transform.shape == (4, 4)

    return transform[:3, :3]


@njit(
    nb.types.Array(nb.float64, 1, "A")(nb.types.Array(nb.float64, 2, "C")),
    fastmath=FAST_MATH,
)
def get_translation(transform):
    # assert transform.shape == (4, 4)

    return transform[:3, 3]


@njit(
    nb.types.Array(nb.float64, 1, "C")(nb.types.Array(nb.float64, 2, "C")),
    fastmath=FAST_MATH,
)
def matrix_to_euler(rotation_matrix):
    # assert rotation_matrix.shape == (3, 3)

    beta = -np.arcsin(rotation_matrix[2, 0])
    cos_beta = np.cos(beta)
    alpha = np.arctan2(
        rotation_matrix[2, 1] / cos_beta,
        rotation_matrix[2, 2] / cos_beta,
    )
    gamma = np.arctan2(
        rotation_matrix[1, 0] / cos_beta,
        rotation_matrix[0, 0] / cos_beta,
    )
    return np.asarray((alpha, beta, gamma))
