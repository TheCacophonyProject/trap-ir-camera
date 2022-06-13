import os
import cv2
from motion import Motion
from logs import init_logging
from datetime import datetime
import socket
import logging

USB_DIR = "/home/gp/"
VIDEO_DIR = os.path.join(USB_DIR, "videos")

STILL_DIR = "/var/spool/cptv"
FPS = 10
H264_EXT = ".h264"
MP4_EXT = ".mp4"
RESOLUTION = (640, 480)
FOURCC = cv2.VideoWriter_fourcc(*"XVID")
HOSTNAME = socket.gethostname()

MIN_FRAMES = 10 * FPS
MAX_FRAMES = 120 * FPS


def run_recorder(frame_queue):
    init_logging()
    motion_detector = Motion()
    recording = False
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

    def close(self):
        if self.recording:
            logging.info("Stopping recording")
            self.writer.release()
            self.recording = False

    def process_frame(self, frame):
        motion = self.motion_detector.process_frame(frame.copy())

        if not self.recording and motion:
            self.length = 0
            out_file = get_out_file()
            logging.info(f"Starting new recording: {out_file}")
            self.writer = cv2.VideoWriter(
                out_file, FOURCC, FPS, (self.res_x, self.res_y)
            )
            self.recording = True
            cv2.imwrite(os.path.join(STILL_DIR, "still.png"), frame)
            previews = self.motion_detector.preview_frames.get_frames()
            logging.info("got %s previews", len(previews))
            for f in previews:
                self.writer.write(f)
            # buffer.clear()
        elif (self.recording and not motion and self.length > MIN_FRAMES) or (
            self.length >= MAX_FRAMES
        ):
            logging.info("Stopping recording")
            self.writer.release()
            self.recording = False
        elif self.recording:
            self.writer.write(frame)
            self.length += 1


def get_out_file():
    date_str = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
    file_name = f"{date_str}_{HOSTNAME}.avi"
    return os.path.join(VIDEO_DIR, file_name)
