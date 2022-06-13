from threading import Lock

import numpy as np
import cv2
import time
import logging


class Background:
    BACKGROUND_WEIGHT_ADD = 0.01

    def __init__(self):
        self.background = None
        self.background_weight = None
        self.frames = 0

    def process_frame(self, frame):
        self.frames += 1
        if self.background is None:
            self.background = frame
            self.background_weight = np.zeros((frame.shape), dtype=np.float32)
            return
        # new backgound is a rolling minimum of frames per pixel,
        # i.e. if frame[0][0]  - self.background_weight[0][0] < self.background[0][0]
        #  background[0][0]  = frame[0][0]
        # else
        #  background[0][0] remains unchanged and background_weight[0][0] is added too
        # this forces a change every now and again
        new_background = np.where(
            self.background < frame - self.background_weight,
            self.background,
            frame,
        )
        # update weighting
        self.background_weight = np.where(
            self.background < frame - self.background_weight,
            self.background_weight + Background.BACKGROUND_WEIGHT_ADD,
            0,
        )


class SlidingWindow:
    def __init__(self, size):
        self.lock = Lock()
        # might not need lock
        self.frames = [None] * size
        self.last_index = None
        self.size = len(self.frames)
        self.oldest_index = None

    def update_current_frame(self, frame):
        with self.lock:
            if self.last_index is None:
                self.oldest_index = 0
                self.last_index = 0
            self.frames[self.last_index] = frame

    @property
    def current(self):
        with self.lock:
            if self.last_index is not None:
                return self.frames[self.last_index]
            return None

    def get_frames(self):
        with self.lock:
            if self.last_index is None:
                return []
            frames = []
            cur = self.oldest_index
            end_index = (self.last_index + 1) % self.size
            while len(frames) == 0 or cur != end_index:
                frames.append(self.frames[cur])
                cur = (cur + 1) % self.size
            return frames

    def get(self, i=None):
        if i is None:
            return self.current()
        i = i % self.size
        with self.lock:
            return self.frames[i]

    @property
    def oldest(self):
        with self.lock:
            if self.oldest_index is not None:
                return self.frames[self.oldest_index]
            return None

    def add(self, frame):
        with self.lock:
            if self.last_index is None:
                # init
                self.oldest_index = 0
                self.frames[0] = frame
                self.last_index = 0
            else:
                new_index = (self.last_index + 1) % self.size
                if new_index == self.oldest_index:
                    self.oldest_index = (self.oldest_index + 1) % self.size
                self.frames[new_index] = frame
                self.last_index = new_index

    def reset(self):
        with self.lock:
            self.last_index = None
            self.oldest_index = None


FPS = 10
WINDOW_SIZE = 5 * FPS


class Motion:
    def __init__(self):
        self.preview_frames = SlidingWindow(WINDOW_SIZE)
        self.background = Background()
        self.kernel_trigger = np.ones(
            (15, 15), "uint8"
        )  # kernel for erosion when not recording
        self.kernel_recording = np.ones(
            (10, 10), "uint8"
        )  # kernel for erosion when recording
        self.motion = (
            False  # If there is currently considered to be motion in the video
        )
        self.motion_count = 0
        self.show = False

    def get_kernel(self):
        if self.motion:
            return self.kernel_recording
        else:
            return self.kernel_trigger

    # Processes a frame returning True if there is motion.
    def process_frame(self, frame):
        self.background.process_frame(frame)
        if self.background.frames < WINDOW_SIZE:
            self.preview_frames.add(frame)
            return False

        # Filter and get diff from background
        delta = cv2.absdiff(
            self.preview_frames.current, frame
        )  # Get delta from current frame and background
        threshold = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
        erosion_image = cv2.erode(threshold, self.get_kernel())
        erosion_pixels = len(erosion_image[erosion_image > 0])
        # to do find a value that suites the number of pixesl we want to move
        self.preview_frames.add(frame)

        # Calculate if there was motion in the current frame
        # TODO Chenage how much is added to the motion_count depending on how big the motion is
        if erosion_pixels > 0:
            self.motion_count += 1
            self.motion_count = max(self.motion_count, 30)
        else:
            self.motion_count -= 1
            self.motion_count = min(self.motion_count, 0)

        # logging.info("motion count is %s", self.motion_count)
        # Check if motion has started or ended
        if not self.motion and self.motion_count > 10:
            self.motion = True

        elif self.motion and self.motion_count <= 0:
            self.motion = False

        if self.show:
            cv2.imshow("delta", delta)
            cv2.imshow("threshold", threshold)
            cv2.imshow("erosion_image", erosion_image)
            cv2.imshow("window", frame)
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
