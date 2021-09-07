#!/usr/bin/python3

import cv2
import time

fps = 10

recording_length_seconds = 60

cap1 = cv2.VideoCapture(0)
cap2 = cv2.VideoCapture(2)

width1 = int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH))
height1 = int(cap1.get(cv2.CAP_PROP_FRAME_HEIGHT))

width2 = int(cap2.get(cv2.CAP_PROP_FRAME_WIDTH))
height2 = int(cap2.get(cv2.CAP_PROP_FRAME_HEIGHT))


print(width1)
print(height1)

print(width2)
print(height2)

fourcc = cv2.VideoWriter_fourcc(*'XVID')
writer1 = cv2.VideoWriter("output1.avi", fourcc, fps, (640, 480))
writer2 = cv2.VideoWriter("output2.avi", fourcc, fps, (640, 480))

prev = 0
capturing = True
frame_count = 0
while capturing:
    time_elapsed = time.time() - prev
    res, frame1 = cap1.read()
    res, frame2 = cap2.read()

    if time_elapsed > 1./fps:
        frame_count += 1
        prev = time.time()
        writer1.write(frame1)
        writer2.write(frame2)
        if frame_count > fps*recording_length_seconds:
            break

cap1.release()
cap2.release()
writer1.release()
writer2.release()
