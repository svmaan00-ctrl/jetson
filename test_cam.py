import cv2
import os

# Die Pipeline, die in Ihrem Terminal-Test funktioniert hat
# WICHTIG: appsink muss am Ende stehen!
pipeline = (
    "v4l2src device=/dev/video0 num-buffers=1 ! "
    "image/jpeg, width=1280, height=960 ! "
    "jpegparse ! jpegdec ! videoconvert ! "
    "video/x-raw, format=BGR ! appsink"
)

print("Versuche Kamera zu öffnen...")
cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("FEHLER: OpenCV kann die GStreamer-Pipeline nicht öffnen.")
    print("Prüfung: Hat OpenCV GStreamer-Support?")
    print(cv2.getBuildInformation())
else:
    ret, frame = cap.read()
    if ret:
        cv2.imwrite("test_bild.jpg", frame)
        print("ERFOLG: 'test_bild.jpg' wurde gespeichert!")
    else:
        print("FEHLER: Pipeline offen, aber kein Frame empfangen.")

cap.release()