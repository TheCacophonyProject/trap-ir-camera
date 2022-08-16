#!/usr/bin/python3
import cv2
import psutil
import socket
import logging
import sys
import os
import shutil
from datetime import datetime
import glob
import argparse
import numpy as np
import subprocess
import time

from pathlib import Path
import multiprocessing

MAX_DISK_USAGE_PERCENT = 80
USB_DIR = "/media/cp"
VIDEO_DIR = os.path.join(USB_DIR, "videos")
TMP_DIR = "/tmp"
VIDEO_DIR = "/var/spool/cptv"
STILL_DIR = "/var/spool/cptv"
FPS = 10
H264_EXT = ".h264"
RESOLUTION = (640, 480)
#FOURCC = cv2.VideoWriter_fourcc(*"XVID")
#FOURCC = cv2.VideoWriter_fourcc(*'mp4v')
#FOURCC = cv2.VideoWriter_fourcc('V','P','8','0')
#VIDEO_EXT = "avi"
FOURCC = cv2.VideoWriter_fourcc(*'avc1')
VIDEO_EXT = "mp4"
MIN_FRAMES = 10 * FPS
MAX_FRAMES = 120 * FPS
FPS = 10
WINDOW_SIZE = 5 * FPS
PRINT_WAIT_TIMES = True

VERSION = 2.0
hostname = socket.gethostname()


def init_logging():
    fmt = "%(process)d %(thread)s:%(levelname)7s %(message)s"
    logging.basicConfig(
        stream=sys.stderr, level=logging.INFO, format=fmt, datefmt="%Y-%m-%d %H:%M:%S"
    )

def need_more_disk_space():
    return psutil.disk_usage(VIDEO_DIR).percent > MAX_DISK_USAGE_PERCENT

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source",
        help='a Mp4/avi file to process, or a folder name, or "all" for all files within subdirectories of source folder.',
    )
    args = parser.parse_args()

    if args.source:
        args.source = Path(args.source)
    print(f"args f{args}")
    return args


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
            self.filename = self.get_file_name()
            self.tmp_file = os.path.join(TMP_DIR, self.filename)
            logging.info(f"Starting new recording: {self.tmp_file}")
            self.writer = cv2.VideoWriter(
                self.tmp_file, FOURCC, FPS, (self.res_x, self.res_y)
            )
            self.recording = True
            cv2.imwrite(os.path.join(STILL_DIR, "still.png"), frame)
            previews = self.motion_detector.preview_frames.get_frames()
            self.writer.write(self.motion_detector.get_background())
            for f in previews:
                self.writer.write(f)
        elif (self.recording and not motion and self.length > MIN_FRAMES) or (
            self.length >= MAX_FRAMES
        ):
            logging.info("Stopping recording")
            self.writer.release()
            out_file = os.path.join(VIDEO_DIR, self.filename)
            logging.info(f"Saving file to {out_file}")
            os.rename(self.tmp_file, out_file)
            self.recording = False
        elif self.recording:
            self.writer.write(frame)
            self.length += 1

    def get_file_name(self):
        date_str = datetime.utcnow().strftime("%Y-%m-%d_%H.%M.%S")
        return f"{date_str}_{hostname}_{VERSION}.{VIDEO_EXT}"

class Background:
    AVERAGE_OVER = 1000

    def __init__(self):
        self._background = None
        self.frames = 0

    def process_frame(self, frame):
        self.frames += 1
        if self._background is None:
            self._background = np.float32(frame.copy())
            return
        if self.frames < Background.AVERAGE_OVER:
            self._background = (self._background * self.frames + frame) / (
                self.frames + 1
            )
        else:
            self._background = (
                self._background * (Background.AVERAGE_OVER - 1) + frame
            ) / (Background.AVERAGE_OVER)

        self.frames += 1

    @property
    def background(self):
        return np.uint8(self._background)


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

    def get_background(self):
        return self.background.background

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


def main():
    init_logging()

    args = parse_args()
    if args.source is None:
        cap = cv2.VideoCapture(0)
    else:
        cap = cv2.VideoCapture(str(args.source))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    #FPS = int(cap.get(cv2.CAP_PROP_FPS))
    #print(FPS)
    frame_queue = multiprocessing.Queue()
    p_processor = multiprocessing.Process(
        target=run_recorder,
        args=(frame_queue,),
    )
    p_processor.start()

    # Start video capture
    logging.info("Starting video capture")
    headers = {"width": width, "height": height}
    frame_queue.put(headers)
    frame_count = 0.0
    start_time = time.time()
    wait_times = []
    while True:
        # Wait for next capture.
        wait_time = max(0, start_time + frame_count/FPS - time.time())
        time.sleep(wait_time)
        wait_times.append(wait_time)
        returned, frame = cap.read()
        frame_count+=1
        if frame_count%10*FPS == 0 and PRINT_WAIT_TIMES:
            print("wait times between frames:")
            print("Max:", max(wait_times))
            print("Min:", min(wait_times))
            print("Avg:", sum(wait_times)/len(wait_times))
            wait_times = []
        if not returned:
            logging.info("no frame from video capture")
            break
        # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_queue.put(frame)
    frame_queue.put("DONE")
    p_processor.join()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
