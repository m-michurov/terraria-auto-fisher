from typing import Any

import cv2
import numpy as np


__all__ = [
    'MotionDetector'
]


BLUR_KERNEL_SIZE = (17, 17)


def _preprocess(image: np.ndarray) -> np.ndarray:
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image = cv2.GaussianBlur(image, BLUR_KERNEL_SIZE, 0)

    return image


def _clamp(value: Any, min_: Any, max_: Any) -> Any:
    return max(min_, min(max_, value))


class MotionDetector:
    BINARIZATION_THRESHOLD_DEFAULT = 4
    BINARIZATION_THRESHOLD_MIN = 0
    BINARIZATION_THRESHOLD_MAX = 255

    DIFFERENCE_THRESHOLD_DEFAULT = 4
    DIFFERENCE_THRESHOLD_MIN = 0
    DIFFERENCE_THRESHOLD_MAX = 1_000

    SENSITIVITY_DEFAULT = 100
    SENSITIVITY_MIN = 0
    SENSITIVITY_MAX = 1_000

    def __init__(
            self,
            binary_threshold: int = BINARIZATION_THRESHOLD_DEFAULT,
            difference_threshold: int = DIFFERENCE_THRESHOLD_DEFAULT,
            sensitivity: int = SENSITIVITY_DEFAULT
    ) -> None:
        self._binary_threshold: int = binary_threshold
        self._difference_threshold: int = difference_threshold
        self._sensitivity: int = sensitivity

        self._frame_buffer: list[np.ndarray] = list()

    @property
    def difference_threshold(self) -> int:
        return self._binary_threshold

    @difference_threshold.setter
    def difference_threshold(self, value: int) -> None:
        self._difference_threshold = _clamp(
            value, MotionDetector.DIFFERENCE_THRESHOLD_MIN, MotionDetector.DIFFERENCE_THRESHOLD_MAX
        )

    @property
    def sensitivity(self) -> int:
        return self._sensitivity

    @sensitivity.setter
    def sensitivity(self, value: int) -> None:
        self._sensitivity = _clamp(value, MotionDetector.SENSITIVITY_MIN, MotionDetector.SENSITIVITY_MAX)

    def detect(self, frame: np.ndarray) -> tuple[np.ndarray, int, bool]:
        frame = _preprocess(frame)
        height, width = frame.shape[:2]

        self._frame_buffer = (self._frame_buffer[1:] + [frame]) if self._frame_buffer else [frame, frame, frame]

        frame_0, frame_1, frame_2 = self._frame_buffer
        diff_1, diff_2 = cv2.absdiff(frame_0, frame_1), cv2.absdiff(frame_1, frame_2)
        frame_diff = cv2.bitwise_or(diff_1, diff_2)
        _, frame_diff = cv2.threshold(frame_diff, self._binary_threshold, 255, cv2.THRESH_BINARY)

        diff = cv2.countNonZero(frame_diff)
        diff = diff * self._sensitivity // (height * width)

        return frame_diff, diff, diff > self._difference_threshold
