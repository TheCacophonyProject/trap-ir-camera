import os
from dateutil.parser import parse as parse_date
import sys
import argparse
import logging
import cv2
from time import gmtime
from time import strftime
from motion import Motion
from pathlib import Path
import json

from api import API
from multiprocessing import Pool
import multiprocessing
from logging.handlers import QueueHandler, QueueListener

FPS = 10
# MOTION = "motion"
NO_MOTION = "no motion"
import psycopg2


def worker_init(q):
    # all records from worker processes go to qh and then into q
    qh = QueueHandler(q)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(qh)


def logger_init():
    q = multiprocessing.Queue()
    # this is the handler for all log records
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(levelname)s: %(asctime)s - %(process)s - %(message)s")
    )

    # ql gets records from the queue and sends them to the handler
    ql = QueueListener(q, handler)
    ql.start()

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # add the handler to the logger so records from this process are handled
    logger.addHandler(handler)

    return ql, q


class MotionLogger:
    def __init__(self, frame_number):
        self.start = frame_number
        self.end = frame_number

    def stop(self, frame_number):
        self.end = frame_number

    def __str__(self):
        s = strftime("%M:%S", gmtime(self.start / FPS))
        e = strftime("%M:%S", gmtime(self.end / FPS))
        return f"{s}-{e}"


def init_logging(timestamps=False):
    """Set up logging for use by various classifier pipeline scripts.

    Logs will go to stderr.
    """

    fmt = "%(process)d %(thread)s:%(levelname)7s %(message)s"
    if timestamps:
        fmt = "%(asctime)s " + fmt
    logging.basicConfig(
        stream=sys.stderr, level=logging.INFO, format=fmt, datefmt="%Y-%m-%d %H:%M:%S"
    )


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "source",
        help='a Mp4/avi file to process, or a folder name, or "all" for all files within subdirectories of source folder.',
    )
    args = parser.parse_args()
    args.source = Path(args.source)
    return args


def load_meta(file):
    meta = file.with_suffix(".txt")
    if meta.exists():
        with meta.open() as f:
            # add in some metadata stats
            meta = json.load(f)
        if meta.get("recordingDateTime"):
            meta["recordingDateTime"] = parse_date(meta["recordingDateTime"])
        if meta.get("tracks") is None and meta.get("Tracks"):
            meta["tracks"] = meta["Tracks"]
        return meta
    return None


def main():
    q_listener, q = logger_init()
    args = parse_args()
    print(args.source.is_file())
    if args.source.is_file():
        print("Is file")
        print("running", args.source)
        process(args.source)
        return
    file_paths = []
    for folder_path, _, files in os.walk(str(args.source)):
        for name in files:
            if os.path.splitext(name)[1] in [".avi", ".mp4"]:
                full_path = os.path.join(folder_path, name)
                file_paths.append(Path(full_path))
    file_paths.sort()
    with Pool(processes=4) as pool:
        pool.map(process, file_paths)
    q_listener.stop()


def process(source):
    try:
        logging.info(source)
        meta = load_meta(source)
        if meta is not None:
            recording_id = meta.get("id")
            for tag in meta.get("tags", []):
                if tag.get("what") == NO_MOTION:
                    logging.info("Already tagged as no motion %s", meta["id"])
                    # return
        logging.info("Processing %s with id %s", source, recording_id)
        motion = Motion()
        vidcap = cv2.VideoCapture(str(source))
        frame_number = 0
        m = None
        motions = []
        recording = False
        while True:
            success, image = vidcap.read()
            if not success:
                break
            # gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            motion.process_frame(image)
            if not recording and motion.motion:
                m = MotionLogger(frame_number)
                logging.info("Motion detected %s", frame_number)
                recording = True
            elif recording and not motion.motion:
                logging.info("Motion Stopped")
                m.stop(frame_number)
                motions.append(m)
                recording = False
                m = None

            # if motion.motion_count > 0:
            # cv2.imshow(f"background", motion.background.get())
            # cv2.imshow("frame", gray)
            # cv2.moveWindow(f"background", 0, 0)
            # cv2.moveWindow(f"frame", 0, 480)
            #
            # cv2.waitKey()

            frame_number += 1
        if m is not None:
            m.stop(frame_number)
            motions.append(m)

        if len(motions) == 0:
            logging.info("no motion")
        cv2.imshow("background", motion.background.background)
        cv2.waitKey()
        for m in motions:
            logging.info("Motion %s ", m)
    except:
        logging.error("Error processing %s", source, exc_info=True)


if __name__ == "__main__":
    main()
