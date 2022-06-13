from threading import Lock

import numpy as np
import cv2
import time
import logging


class Background:
    BACKGROUND_WEIGHT_ADD = 0.001
    STILL_FOR = 200
    # update pixels which have shown no movement for 200 frames
    def __init__(self):
        self.background = None
        # self.background_weight = None
        self.frames = 0

    def process_frame(self, frame):
        self.frames += 1

        if self.background is None:
            self.background = frame.copy()
            # self.background_weight = np.zeros((frame.shape), dtype=np.float32)
            return
        self.background = np.minimum(self.background, frame)
        #
        # indices = np.where(thresh == 0)
        # self.background_weight = np.where(
        #     thresh == 0,
        #     self.background_weight + 1,
        #     0,
        # )
        # self.background = np.where(
        #     self.background_weight > Background.STILL_FOR,
        #     frame,
        #     self.background,
        # )
        # self.background = np.uint8(self.background)
        # self.background_weight[self.background_weight > Background.STILL_FOR] -= (
        #     Background.STILL_FOR / 4.0
        # )
        # np.clip(self.background_weight, a_min=0, a_max=None)


class SlidingWindow:
    def __init__(self, size):
        # might not need lock
        self.frame_len = size
        self.frames = [None] * size
        self.i = 0

    def add(self, frame):
        self.frames[self.i] = frame
        self.i += 1
        self.i = self.i % self.frame_len

    @property
    def oldest(self):
        return self.frames[self.i]

    def get_frames(self):
        frames = []
        cur = self.i
        # end_index = (cur + 1) % self.frame_len
        while len(frames) == 0 or cur != self.i:
            frames.append(self.frames[cur])
            cur = (cur + 1) % self.frame_len
        return frames


FPS = 10
WINDOW_SIZE = 5 * FPS


class Motion:
    def __init__(self):
        self.preview_frames = SlidingWindow(WINDOW_SIZE)
        self.preview_frames_grey = SlidingWindow(WINDOW_SIZE)

        self.background = Background()
        self.kernel_trigger = np.ones(
            (15, 15), "uint8"
        )  # kernel for erosion when not recording
        self.kernel_recording = np.ones(
            (10, 10), "uint8"
        )  # kernel for erosion when recording
        self.motion = False
        self.motion_count = 0
        self.show = False

    def get_kernel(self):
        if self.motion:
            return self.kernel_recording
        else:
            return self.kernel_trigger

    # Processes a frame returning True if there is motion.
    def process_frame(self, frame):
        self.preview_frames.add(frame)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.preview_frames_grey.add(frame)

        if self.preview_frames_grey.oldest is None:
            return False

        # Filter and get diff from background
        delta = cv2.absdiff(
            self.preview_frames_grey.oldest, frame
        )  # Get delta from current frame and background
        threshold = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]

        erosion_image = cv2.erode(threshold, self.get_kernel())
        erosion_pixels = len(erosion_image[erosion_image > 0])
        # to do find a value that suites the number of pixesl we want to move
        self.preview_frames_grey.add(frame)
        self.background.process_frame(frame)

        # Calculate if there was motion in the current frame
        # TODO Chenage how much ioldests added to the motion_count depending on how big the motion is
        if erosion_pixels > 0:
            self.motion_count += 1
            self.motion_count = min(self.motion_count, 30)
        else:
            self.motion_count -= 1
            self.motion_count = max(self.motion_count, 0)

        # logging.info("motion count is %s", self.motion_count)
        # Check if motion has started or ended
        if not self.motion and self.motion_count > 10:
            self.motion = True

        elif self.motion and self.motion_count <= 0:
            self.motion = False

        if self.show:
            cv2.imshow("window", frame)
            cv2.imshow("delta", delta)
            cv2.imshow("threshold", threshold)
            cv2.imshow("erosion_image", erosion_image)
            cv2.imshow("background", self.background.background)

            cv2.moveWindow(f"window", 0, 0)
            cv2.moveWindow(f"delta", 640, 0)
            cv2.moveWindow(f"erosion_image", 0, 480)
            cv2.moveWindow(f"threshold", 640, 480)
            cv2.moveWindow(f"background", 1000, 960)

            cv2.waitKey(1)

        return self.motion


# Example
"""
cap = cv2.VideoCapture(0)
motion = Motion()
motion.show = True
while True:
    returned, frame = cap.read()
    if not returned:
        print("no frame from video capture")
        break
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    motion.process_frame(frame)
cv2.destroyAllWindows()
"""
