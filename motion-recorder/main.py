#!/usr/bin/python3

from motion import Motion
import cv2
import psutil
import socket
from systemd.journal import JournalHandler
import logging
import sys
import os
import shutil
from datetime import datetime
import glob
import collections
import time
import subprocess

motion = Motion()

cap = cv2.VideoCapture(0)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#print(width)
#print(height)
fps = 10.0
# cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
fourcc = cv2.VideoWriter_fourcc(*'XVID')


motion = Motion()
motion.show = False
recording = False

usb_dir = '/media/cp'
video_dir = os.path.join(usb_dir, 'videos')
still_dir = '/var/spool/cptv'
h264_ext = ".h264"
mp4_ext = ".mp4"
resolution = (640,480)
hostname = socket.gethostname()
max_disk_usage_percent = 80

log = logging.getLogger('demo')
log.addHandler(JournalHandler())
stdout_handleer = logging.StreamHandler(sys.stdout)
stdout_handleer.setFormatter(logging.Formatter('%(message)s'))
stdout_handleer.setLevel(logging.INFO)
log.addHandler(stdout_handleer)
log.setLevel(logging.INFO)


buffer = collections.deque(maxlen=1)# TODO Can't increase this without the writing process being it it's own thread

def need_more_disk_space():
    return psutil.disk_usage(video_dir).percent > max_disk_usage_percent

def get_out_file():
    date_str = datetime.now().strftime('%Y-%m-%d_%H.%M.%S')
    file_name = f'{date_str}_{hostname}.avi'
    return os.path.join(video_dir, file_name)

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
        if os.path.isfile(f) and not f.endswith(f'{hostname}{mp4_ext}'):
            os.remove(f)
        elif os.path.isdir(f):
            shutil.rmtree(f)


# Check if USB is properly mounted
log.info("checking USB is mounted....")
if usb_dir not in subprocess.check_output('df').decode('utf-8'):
    log.info(f"USB not mounted at {usb_dir}")
    sys.exit(f"USB not mounted at {usb_dir}")
log.info("done")

os.makedirs(video_dir, exist_ok=True)
os.makedirs(still_dir, exist_ok=True)
log.info("Starting video capture")



frame_count = 0
while True:
    returned, frame = cap.read()
    if not returned:
        log.info("no frame from video capture")
        break
    #frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    #print(frame.size)
    motion.process_frame(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    
    if not recording: # and motion.motion:
        out_file = get_out_file()
        log.info(f"Starting new recording: {out_file}")
        writer = cv2.VideoWriter(out_file, fourcc, fps, (width, height))
        recording = True
        cv2.imwrite(os.path.join(still_dir, 'still.png'), frame)
        for f in buffer:
            writer.write(f)
        buffer.clear()
    elif frame_count > fps * 120: ##recording and not motion.motion
        log.info("Stopping recording")
        writer.release()
        recording = False
        frame_count = 0

    if recording:
        frame_count += 1
        writer.write(frame)
    else:
        buffer.append(frame)

cv2.destroyAllWindows()