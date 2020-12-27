from __future__ import print_function
import os
import time
import datetime
import numpy as np
import cv2
from face_finder import FaceFinder
from recognizer import Recognizer
from strangers import Clusterizer
import video_maker
import encode
from emotions import Emanalisis
import shutil
import json


class ROFL:

    def __init__(self, recognizer_path, retina=False, on_gpu=False, emotions=False,
                 confidence_threshold=0.02,
                 top_k=5000,
                 nms_threshold=0.4,
                 keep_top_k=750,
                 vis_thres=0.6,
                 network='resnet50',
                 distance_threshold=0.4,
                 samples=5,
                 eps=0.3):
        self.on_gpu = on_gpu

        if retina:
            self.finder = FaceFinder(on_gpu=on_gpu, confidence_threshold=confidence_threshold,
                                     top_k=top_k, nms_threshold=nms_threshold, keep_top_k=keep_top_k,
                                     vis_thres=vis_thres, network=network)
        else:
            self.finder = None

        if emotions:
            self.emotions = Emanalisis(on_gpu=on_gpu, path_to_classifier="net_714.pth", finder=self.finder)
        else:
            self.emotions = None

        self.recognizer_retrained = True
        self.recog = Recognizer(finder=self.finder, distance_threshold=distance_threshold)
        self.recog.load_model(recognizer_path)
        self.clust = Clusterizer(samples=samples, eps=eps)
        self.em_labels = ['ANGRY', 'DISGUST', 'FEAR', 'HAPPY', 'SAD', 'SURPRISE', 'NEUTRAL']

    def load_video(self, video, fps_factor):
        """load video for analysis.
        :param video - string, name of the file
        :param fps_factor - int/float, which fps output will be, mainly used for lowering amount of frames taken to analyse
        :returns array of images of corresponding fps"""

        cap = cv2.VideoCapture(video)
        # fps = cap.get(cv2.CAP_PROP_FPS)
        # cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        # t = time.time()
        ret = True
        # os.chdir(r"frames")
        out_arr = []
        i = 0
        while ret:
            ret, frame = cap.read()
            if i % fps_factor == 0:
                # t = time.time()
                out_arr.append(frame)
                # cv2.imwrite("frame " + str(count_frames) + ".jpg", frame)
            i += 1
        return np.asarray(out_arr), cap.get(cv2.CAP_PROP_FPS)

    def analyse(self, img_arr, recognize=False, emotions=False, one_array=False):
        face_predictions = []
        em_predictions = []
        i = 1
        for img in img_arr:
            if i == 2:
                t = time.time()
            face_loc = self.finder.detect_faces(img)
            if recognize:
                face_predictions.append(self.recog.predict(img, X_face_locations=face_loc))
            if emotions:
                em_predictions.append(self.emotions.classify_emotions(img, face_locations=face_loc))
            if i == 2:
                t = (time.time() - t) * len(img_arr)
                m = t // 60
                s = t % 60
                print("Approximately " + str(m) + " minutes and " + str(s) + " seconds to make predictions")
            print(str(i / len(img_arr) * 100) + "% of video is done")
            i += 1
        if one_array:
            out_array = []
            if recognize and emotions:
                for em, face in zip(em_predictions, face_predictions):
                    buf = []
                    for e, f in zip(em, face):
                        buf.append((e[1], self.em_labels[np.argmax(e[0])], f[0]))
                    out_array.append(buf)
            elif recognize:
                for face in face_predictions:
                    buf = []
                    for f in face:
                        buf.append((f[1], None, f[0]))
                    out_array.append(buf)
            elif emotions:
                for em in em_predictions:
                    buf = []
                    for e in em:
                        buf.append((e[1], self.em_labels[np.argmax(e[0])], None))
                    out_array.append(buf)
            return out_array

        return face_predictions, em_predictions

    def find_emotions(self, img_arr):
        predictions = []
        i = 1
        for img in img_arr:
            if i == 2:
                t = time.time()
            predictions.append(self.emotions.classify_emotions(img))
            if i == 2:
                t = (time.time() - t) * len(img_arr)
                m = t // 60
                s = t % 60
                print("Approximately " + str(m) + " minutes and " + str(s) + " seconds to find faces")
            print(str(i / len(img_arr) * 100) + "% of video is done")
            i += 1
        return predictions

    def basic_run(self, in_dir, filename, fps_factor=1, recognize=False, remember=False, emotions=False):
        orig_img_arr, orig_fps = self.load_video(in_dir + "/" + filename, fps_factor)
        new_fps = orig_fps / fps_factor

        face_predictions, em_predictions = self.analyse(orig_img_arr, recognize=recognize, emotions=emotions)

        if recognize:
            img_arr = video_maker.boxes(orig_img_arr, predictions=face_predictions, headcount=True, faces_on=recognize)
        if emotions:
            img_arr = video_maker.emotion_boxes(orig_img_arr, em_predictions, headcount=True, faces_on=recognize)

        filename = video_maker.render("video_output", filename, img_arr, new_fps)

        if remember and recognize:
            for img, pred in zip(orig_img_arr, face_predictions):
                for name, (top, right, bottom, left) in pred:
                    if name == "unknown":
                        # save_img = cv2.cvtColor(img[top:bottom, right:left], cv2.COLOR_BGR2RGB)
                        save_img = img[top:bottom, left:right]
                        # cv2.imshow("Haha", save_img)
                        # cv2.waitKey(0)
                        cv2.imwrite("./strangers/" + datetime.datetime.now().strftime("%d%m%Y%H%M%S%f") + ".jpg",
                                    save_img)

            encode.encode_cluster_sf("./strangers", "./enc_cluster.pickle")
            self.clust.remember_strangers("./enc_cluster.pickle", "./known_faces")
        return filename

    def json_run(self, in_dir, filename, fps_factor=1, recognize=False, remember=False, emotions=False):
        orig_img_arr, orig_fps = self.load_video(in_dir + "/" + filename, fps_factor)
        new_fps = orig_fps / fps_factor

        array = self.analyse(orig_img_arr, recognize=recognize, emotions=emotions, one_array=True)

        # if recognize:
        #     img_arr = video_maker.boxes(orig_img_arr, predictions=face_predictions, headcount=True, faces_on=recognize)
        # if emotions:
        #     img_arr = video_maker.emotion_boxes(orig_img_arr, em_predictions, headcount=True, faces_on=recognize)

        recording = {"name": filename,
                     "fps": new_fps,
                     "config": {
                         "confidence_threshold": self.finder.confidence_threshold,
                         "top_k":self.finder.top_k,
                         "nms_threshold": self.finder.nms_threshold,
                         "keep_top_k": self.finder.keep_top_k,
                         "vis_thres": self.finder.vis_thres,
                         "network": self.finder.network,
                         "distance_threshold": self.recog.distance_threshold,
                         "samples": self.clust.clt.min_samples,
                         "eps": self.clust.clt.eps,
                         "fps_factor": fps_factor
                     },
                     "frames": array}

        with open('recordings/' + filename.split('.')[0] + '.json', 'w') as f:
            json.dump(recording, f)

        if remember and recognize:
            for img, pred in zip(orig_img_arr, array):
                for (top, right, bottom, left), em, name in pred:
                    if name == "unknown":
                        # save_img = cv2.cvtColor(img[top:bottom, right:left], cv2.COLOR_BGR2RGB)
                        save_img = img[top:bottom, left:right]
                        # cv2.imshow("Haha", save_img)
                        # cv2.waitKey(0)
                        cv2.imwrite("./strangers/" + datetime.datetime.now().strftime("%d%m%Y%H%M%S%f") + ".jpg",
                                    save_img)

            encode.encode_cluster_sf("./strangers", "./enc_cluster.pickle")
            self.clust.remember_strangers("./enc_cluster.pickle", "./known_faces")
        return recording

    async def async_run(self, loop, in_dir, filename, fps_factor=1, recognize=False, remember=False, emotions=False):
        orig_img_arr, orig_fps = await loop.run_in_executor(None, self.load_video, in_dir + "/" + filename, fps_factor)
        # img_arr, orig_fps = self.load_video(in_dir + "/" + filename, fps_factor)
        new_fps = orig_fps / fps_factor
        face_predictions, em_predictions = await loop.run_in_executor(None, self.analyse, in_dir, filename,
                                                                      fps_factor, recognize, remember, emotions)
        # face_predictions, em_predictions = self.analyse(img_arr, recognize=recognize, emotions=emotions)

        img_arr = video_maker.boxes(orig_img_arr, predictions=face_predictions, headcount=True, faces_on=recognize)

        filename = video_maker.render("video_output", filename, img_arr, new_fps)

        if remember:
            for img, pred in zip(img_arr, face_predictions):
                for name, (top, right, bottom, left) in pred:
                    if name == "unknown":
                        # save_img = cv2.cvtColor(img[top:bottom, right:left], cv2.COLOR_BGR2RGB)
                        save_img = img[top:bottom, left:right]
                        # cv2.imshow("Haha", save_img)
                        # cv2.waitKey(0)
                        cv2.imwrite("./strangers/" + datetime.datetime.now().strftime("%d%m%Y%H%M%S%f") + ".jpg",
                                    save_img)

            # encode.encode_cluster("./strangers", "./enc_cluster.pickle")
            await loop.run_in_executor(None, encode.encode_cluster_sf, "./strangers", "./enc_cluster.pickle")
            await loop.run_in_executor(None, self.clust.remember_strangers, "./enc_cluster.pickle", "./known_faces")
            # self.clust.remember_strangers("./enc_cluster.pickle", "./known_faces")

        return filename

    def run_from_queue(self, fps_factor=1, recognize=False, remember=False, emotions=False):

        f = open("queue.txt")
        q = [line.strip() for line in f]
        filename = None
        if len(q) > 0:
            filename = self.basic_run("queue", q[0].replace("\n", "").split("/")[1], fps_factor=fps_factor,
                                      emotions=emotions, recognize=recognize, remember=remember)
            os.remove(q[0])
            q.remove(q[0])

        f.close()
        if len(q) > 0:
            f = open("queue.txt", "w")
            for line in q:
                f.write(line + "\n")
            f.close()
        else:
            f = open("queue.txt", "w")
            f.close()
        return filename

    # async def async_load_video(self, video, fps_factor):    # Хз вообще, попробую TODO try to speed-up video loading
    #     pass

    async def async_run_from_queue(self, loop, fps_factor=1, recognize=False, remember=False, emotions=False):
        f = open("queue.txt")
        q = [line.strip() for line in f]
        filename = None
        if len(q) > 0:
            filename = await self.async_run(loop, "queue", q[0].replace("\n", "").split("/")[1], fps_factor=fps_factor,
                                            emotions=emotions, recognize=recognize, remember=remember)
            os.remove(q[0])
            q.remove(q[0])

        f.close()
        if len(q) > 0:
            f = open("queue.txt", "w")
            for line in q:
                f.write(line + "\n")
            f.close()
        else:
            f = open("queue.txt", "w")
            f.close()
        return filename

    def update_queue(self, filename):
        f = open("queue.txt", "a")
        f.write(filename + "\n")
        f.close()

    def add_person(self, name, filename=None):
        os.mkdir('known_faces/' + name)
        if filename is not None:
            shutil.move(filename, "known_faces/" + name + "/" + filename.split('/')[-1])
            self.recognizer_retrained = False

    def add_pics(self, name, filenames):
        for file in filenames:
            shutil.move(file, "known_faces/" + name + "/" + file.split('/')[-1])
        self.recognizer_retrained = False
