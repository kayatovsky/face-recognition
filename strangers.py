from sklearn.cluster import DBSCAN
import numpy as np
import pickle
import cv2
import os
import datetime
import random


class Clusterizer:

    def __init__(self, cpus=-1, samples=5, eps=0.3):
        self.clt = DBSCAN(eps=eps, metric="euclidean", n_jobs=cpus, min_samples=samples)

    def find_clusters(self, enc_path):
        print("[INFO] loading encodings...")
        data = pickle.loads(open(enc_path, "rb").read())
        data = np.array(data)
        encodings = [d["encoding"] for d in data]
        print("[INFO] clustering...")
        self.clt.fit(encodings)
        return self.clt.labels_

    def remember_strangers(self, enc_path, save_path=os.path.dirname(__file__)):
        data = pickle.loads(open(enc_path, "rb").read())
        data = np.array(data)
        # encodings = [d["encoding"] for d in data]
        labels = self.find_clusters(enc_path)
        cluster_nums = np.unique(labels)

        clustered_img = []

        for cluster in cluster_nums:
            if cluster == -1:
                indx = np.where(labels == cluster)[0]
                for i in indx:
                    clustered_img.append(data[i]["imagePath"])
            else:
                indx = np.where(labels == cluster)[0]
                # new_dir = save_path + "/stranger_" + datetime.datetime.now().strftime("%d%m%Y%H%M")
                new_dir = os.path.join(save_path, "stranger_" + datetime.datetime.now().strftime("%d%m%Y%H%M%S%f"))
                os.mkdir(new_dir)
                for i in indx:
                    image = cv2.imread(data[i]["imagePath"])
                    (top, right, bottom, left) = data[i]["loc"]
                    face = image[top:bottom, left:right]
                    cv2.imwrite(new_dir + "/" + str(random.random()) + ".jpg", face)
                    clustered_img.append(data[i]["imagePath"])
        for img in clustered_img:
            os.remove(img)

