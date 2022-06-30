#!/usr/bin/python3
from motion import Motion
import cv2
import psutil
import socket
import logging
import sys
import os
import shutil
from datetime import datetime
import glob
import collections
import time
import argparse

from logs import init_logging
from recorder import run_recorder
from pathlib import Path
import multiprocessing

# hostname = socket.gethostname()
max_disk_usage_percent = 80

USB_DIR = "/tmp"


def need_more_disk_space():
    return psutil.disk_usage(video_dir).percent > max_disk_usage_percent


# Delete everything on the USB drive apart from videos from device in the video directory
def delete_other_files():
    # Delete directories apart from the video_dir
    files = os.listdir(usb_dir)
    for f in files:
        p = os.path.join(usb_dir, f)
        if os.path.basename(p) != os.path.basename(video_dir):
            if os.path.isfile(p):
                os.remove(p)
            else:
                shutil.rmtree(p)

    # Delete all files that are not recording from this device
    files = glob.glob(os.path.join(video_dir, "*"))
    for f in files:
        if os.path.isfile(f) and not f.endswith(f"{hostname}{mp4_ext}"):
            os.remove(f)
        elif os.path.isdir(f):
            shutil.rmtree(f)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source",
        help='a Mp4/avi file to process, or a folder name, or "all" for all files within subdirectories of source folder.',
    )
    args = parser.parse_args()
    args.source = Path(args.source)
    return args


def main():
    init_logging()

    args = parse_args()
    if args.source is None:
        cap = cv2.VideoCapture(0)
    else:
        cap = cv2.VideoCapture(str(args.source))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_queue = multiprocessing.Queue()
    p_processor = multiprocessing.Process(
        target=run_recorder,
        args=(frame_queue,),
    )
    p_processor.start()
    # Check if USB is properly mounted
    logging.info("checking USB is mounted....")
    if not os.path.isdir(USB_DIR):
        logging.info(f"USB not mounted at {USB_DIR}")
        sys.exit(f"USB not mounted at {USB_DIR}")
    logging.info("done")

    logging.info("Starting video capture")
    headers = {"width": width, "height": height}
    frame_queue.put(headers)
    while True:
        returned, frame = cap.read()
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
