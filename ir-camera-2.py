#!/usr/bin/python3

import cv2
import time
import datetime as dt
import os
import logging
from systemd.journal import JournalHandler
import socket
import sys
import shutil
import glob
import psutil
import numpy as np

USB_DIR = '/media/cp'
VIDEO_DIR = os.path.join(USB_DIR, 'videos')
STILL_DIR = '/var/spool/cptv'
VIDEO_EXT = ".avi"
FPS = 10.0
RES_X = 640
RES_Y = 480
HOSTNAME = socket.gethostname()
MAX_DISK_USAGE = 80
RECORDING_LENGTH_SECONDS = 60
MAX_DISK_USAGE_PRECENT = 80

def make_file_name(datetime, camera_name):
    return os.path.join(VIDEO_DIR, datetime.strftime(f'%Y-%m-%d_%H.%M.%S_{camera_name}_{HOSTNAME}{VIDEO_EXT}'))

def need_more_disk_space():
    return psutil.disk_usage(VIDEO_DIR).percent > MAX_DISK_USAGE_PRECENT

def delete_oldest_video():
    files = os.listdir(VIDEO_DIR)
    files.sort()
    log.info(f"deleting '{files[0]}' to make space on USB")
    os.remove(os.path.join(VIDEO_DIR, files[0]))

# Delete everything on the USB drive apart from videos from device in the video directory
def delete_other_files():
    # Delete directories apart from the video directory
    files = os.listdir(USB_DIR)
    for f in files:
        p = os.path.join(USB_DIR, f)
        if os.path.basename(p) != os.path.basename(VIDEO_DIR):
            if os.path.isfile(p):
                os.remove(p)
            else:
                shutil.rmtree(p)

    # Delete all files that are not recording from this device
    files = glob.glob(os.path.join(VIDEO_DIR, "*"))
    for f in files:
        if os.path.isfile(f) and not f.endswith(f'{HOSTNAME}{VIDEO_EXT}'):
            os.remove(f)
        elif os.path.isdir(f):
            shutil.rmtree(f)


# Setup loging to stdout and systemd
log = logging.getLogger('demo')
log.addHandler(JournalHandler())
stdout_handleer = logging.StreamHandler(sys.stdout)
stdout_handleer.setFormatter(logging.Formatter('%(message)s'))
stdout_handleer.setLevel(logging.INFO)
log.addHandler(stdout_handleer)
log.setLevel(logging.INFO)

# Check if USB is properly mounted
log.info("checking USB is mounted....")
if not os.path.isdir(USB_DIR):
    log.info(f"USB not mounted at {USB_DIR}")
    sys.exit(f"USB not mounted at {USB_DIR}")
log.info("done")

# Create required directories
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(STILL_DIR, exist_ok=True)

# Delete other files on the USB
log.info("deleting other files on the USB....")
delete_other_files()
log.info("done")

# Init USB cameras
log.info("initializing cameras....")
#camera1 = cv2.VideoCapture(0)
#camera2 = cv2.VideoCapture(2)

cameras = [
    {
        'name': "1",
        'camera': cv2.VideoCapture(0),
        'frame': None,
        'writer': None,
    },
    {
        'name': "2",
        'camera': cv2.VideoCapture(2),
        'frame': None,
        'writer': None,
    }]
    

codec = 1196444237.0 # MJPG
for camera in cameras:
    camera['camera'].set(cv2.CAP_PROP_FPS, FPS)
    camera['camera'].set(cv2.CAP_PROP_FRAME_WIDTH, RES_X)
    camera['camera'].set(cv2.CAP_PROP_FRAME_HEIGHT, RES_Y)
    camera['camera'].set(cv2.CAP_PROP_FOURCC, codec)
    #camera['camera'].set(cv2.CAP_PROP_FOURCC, cv2.CV_FOURCC('M', 'J', 'P', 'G'))
    _, _ = camera['camera'].read()
fourcc = cv2.VideoWriter_fourcc(*'XVID')
#fourcc = cv2.VideoWriter_fourcc(*'MJPG')
log.info("done")


while True:
    log.info("checking for enough disk space on USB")
    while (need_more_disk_space()):
        delete_oldest_video()
    frame_count = 0
    now = dt.datetime.now()
    for camera in cameras:
        camera['writer'] = cv2.VideoWriter(make_file_name(now, camera['name']), fourcc, FPS, (RES_X, RES_Y))
    #writer1 = cv2.VideoWriter(make_file_name(now, "1"), fourcc, FPS, (RES_X, RES_Y))
    #writer2 = cv2.VideoWriter(make_file_name(now, "2"), fourcc, FPS, (RES_X, RES_Y))
    log.info(f"new recordings starting {now.strftime('%Y-%m-%d_%H.%M.%S')}")
    start_time = time.time()
    frames = []
    for camera in cameras:
        _, _ = camera['camera'].read()
        read = False
        while read == False:    
            read, f = camera['camera'].read()
        frames.append(f)
    vis = np.concatenate(frames, axis=0)
    cv2.imwrite(os.path.join(STILL_DIR, 'out.png'), vis)

    while True:
        for camera in cameras:
            _, camera['frame'] = camera['camera'].read()

        if time.time()-start_time > 1./FPS * frame_count:
            frame_count += 1
            for camera in cameras:
                camera['writer'].write(camera['frame'])
            if frame_count > FPS*RECORDING_LENGTH_SECONDS:
                break # break and start new recording
    for camera in cameras:
        camera['writer'].release()
    
    #writer1.release()
    #writer2.release()