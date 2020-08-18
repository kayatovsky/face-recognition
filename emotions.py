from __future__ import print_function
import time
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import cv2
import torch
import face_recognition
from face_finder import FaceFinder


class Classifier(nn.Module):
    """ class for classifier based on pytorch """
    def __init__(self):
        super(Classifier, self).__init__()
        # device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.conv1 = nn.Conv2d(1, 6, 5)  # # # TODO<<"^~^">>TODO
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(6, 24, 5)
        self.fc1 = nn.Linear(24 * 9 * 9, 486)
        self.fc2 = nn.Linear(486, 84)
        self.fc3 = nn.Linear(84, 7)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = x.view(-1, 24 * 9 * 9)
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x


class Emanalisis:
    """ main class for usage in emotion recognition
    input mode - int, determines where class takes its data.
        0 - from default webcam of device
        1 - from ip camera
        2 - from video
    output mode - int, determines how output would look.
        0 - classical opencv display, augments original video
        1 - makes separate graph of emotions count with matplotlib. if record_video is True, will record only graph
        2 - graph on black background with all info. Needed for nvr
    record_video - bool, if True, will record output on mp4.
    email_to_share - list of strings/string, email(s) to share sheet. If there is none, sheets will be barely reachable
    channel - int/string, sourse for input data. If input_mode is 0, it should be 0, if input_mode is 1, it'd be ip
        address of camera, else it is name of mp4 video file
    on_gpu - bool, if true, will use gpu for detection and classification. NEVER USE IF THERE IS NO GPU DEVICE.
    display - bool, if true, will show output on screen.
    only_headcount - bool, if true, will disable classification and graph drawing
    send_to_nvr - bool, if true, will send recorded video into miem nvr"""
    def __init__(self, on_gpu=False, path_to_classifier=None, finder=None):
        self.on_gpu = on_gpu
        # from classifier by Sizykh Ivan

        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

        # PATH = "./check_points_4/net_714.pth"
        if self.on_gpu:
            self.classifier = Classifier().to(self.device)
            self.classifier.load_state_dict(torch.load(path_to_classifier))
        else:
            self.classifier = Classifier()
            self.classifier.load_state_dict(torch.load(path_to_classifier, map_location={'cuda:0': 'cpu'}))

        self.finder = finder

    def classify_face(self, crop_img):

        dim = (48, 48)
        resized = cv2.resize(crop_img, dim)
        gray_res = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        roi = gray_res
        roi = np.array(roi)
        roi = 2 * (roi.astype("float") / 255.0) - 1

        roi = np.expand_dims(roi, axis=2)
        roi = np.expand_dims(roi, axis=0)
        roi = np.expand_dims(roi, axis=0)
        roi = torch.from_numpy(roi)
        roi = roi.float()
        roi = roi.squeeze(dim=4)
        # make a prediction on the ROI, then lookup the class
        tic = time.time()
        if self.on_gpu:
            preds = self.classifier(roi.to(self.device))[0]
        else:
            preds = self.classifier(roi)[0]
        print(str(time.time() - tic) + " to classify")
        emcount = np.zeros(7)
        emcount[preds.argmax()] += 1
        return emcount

    def classify_emotions(self, img, face_locations=None):

        if face_locations is None:
            if self.finder is None:
                face_locations = face_recognition.face_locations(img)
            elif isinstance(self.finder, FaceFinder):
                face_locations = self.finder.detect_faces(img)

        if len(face_locations) == 0:
            return []

        em_arr = []

        for (top, right, bottom, left) in face_locations:
            # if img[top:bottom, left:right].sum() != 0:
            if img[top:bottom, left:right].size != 0:
                em_arr.append(self.classify_face(img[top:bottom, left:right]))

        return [(em, loc) for em, loc in zip(em_arr, face_locations)]
