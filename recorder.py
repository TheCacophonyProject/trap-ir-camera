import os
import cv2
from logs import init_logging
from datetime import datetime
import socket
import logging

# from thermalconfig import ThermalConfig

USB_DIR = "/media/cp"
VIDEO_DIR = os.path.join(USB_DIR, "videos")

STILL_DIR = "/var/spool/cptv"
FPS = 10
H264_EXT = ".h264"
RESOLUTION = (640, 480)
FOURCC = cv2.VideoWriter_fourcc(*"XVID")
HOSTNAME = socket.gethostname()

MIN_FRAMES = 10 * FPS
MAX_FRAMES = 120 * FPS


def run_recorder(frame_queue):
    init_logging()
    os.makedirs(VIDEO_DIR, exist_ok=True)
    os.makedirs(STILL_DIR, exist_ok=True)
    headers = frame_queue.get()
    width = headers["width"]
    height = headers["height"]
    r = Recorder(width, height)
    frames = 0
    while True:
        frames += 1
        frame = frame_queue.get()
        if isinstance(frame, str):
            logging.info("Got all frames")
            r.close()
            break
        r.process_frame(frame)


class Recorder:
    def __init__(self, res_x, res_y):
        self.motion_detector = Motion()
        self.recording = False
        self.res_x = res_x
        self.res_y = res_y
        self.writer = None
        self.length = 0
        # self.config = ThermalConfig.load_from_file()

    def close(self):
        if self.recording:
            logging.info("Stopping recording")
            self.writer.release()
            self.recording = False

    def process_frame(self, frame):
        motion = self.motion_detector.process_frame(frame.copy())

        if not self.recording and motion:
            self.length = 0
            out_file = self.get_out_file()
            logging.info(f"Starting new recording: {out_file}")
            self.writer = cv2.VideoWriter(
                out_file, FOURCC, FPS, (self.res_x, self.res_y)
            )
            self.recording = True
            cv2.imwrite(os.path.join(STILL_DIR, "still.png"), frame)
            previews = self.motion_detector.preview_frames.get_frames()
            self.writer.write(self.motion_detector.background.background)
            for f in previews:
                self.writer.write(f)
        elif (self.recording and not motion and self.length > MIN_FRAMES) or (
            self.length >= MAX_FRAMES
        ):
            logging.info("Stopping recording")
            self.writer.release()
            self.recording = False
        elif self.recording:
            self.writer.write(frame)
            self.length += 1

    def get_out_file(self):
        date_str = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
        file_name = f"{date_str}_{HOSTNAME}.avi"
        return os.path.join(VIDEO_DIR, file_name)


class Background:
    BACKGROUND_WEIGHT_ADD = 0.001
    STILL_FOR = 200
    # update pixels which have shown no movement for 200 frames
    def __init__(self):
        self.background = None
        self.frames = 0

    def process_frame(self, frame):
        self.frames += 1
        if self.background is None:
            self.background = frame.copy()
            return
        self.background = np.minimum(self.background, frame)


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
