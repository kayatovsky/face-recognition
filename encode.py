from imutils import paths
import face_recognition
import pickle
import cv2
import os
from face_finder import FaceFinder


def encode_cls(path, enc_path, finder=None):

    # grab the paths to the input images in our dataset
    print("[INFO] quantifying faces...")
    imagePaths = list(paths.list_images(path))
    # initialize the list of known encodings and known names
    knownEncodings = []
    knownNames = []

    # loop over the image paths
    for (i, imagePath) in enumerate(imagePaths):
        print("[INFO] processing image {}/{}".format(i + 1, len(imagePaths)))
        name = imagePath.split(os.path.sep)[-2]
        image = cv2.imread(imagePath)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    # detect the (x, y)-coordinates of the bounding boxes
    # corresponding to each face in the input image

        if finder is None:
            boxes = face_recognition.face_locations(rgb, model="hog")
        elif isinstance(finder, FaceFinder):
            boxes = finder.detect_faces(rgb)
        else:
            raise Exception("Unknown type of face detector")
        # compute the facial embedding for the face
        encodings = face_recognition.face_encodings(rgb, boxes)
        # loop over the encodings
        for encoding in encodings:
            # add each encoding + name to our set of known names and
            # encodings
            knownEncodings.append(encoding)
            knownNames.append(name)

    # dump the facial encodings + names to disk
    print("[INFO] serializing encodings...")
    data = {"encodings": knownEncodings, "names": knownNames}
    f = open(enc_path, "wb")
    f.write(pickle.dumps(data))
    f.close()

    return data


def encode_cluster(path, enc_path, finder=None):
    print("[INFO] quantifying faces...")
    imagePaths = list(paths.list_images(path))
    data = []
    # loop over the image paths
    for (i, imagePath) in enumerate(imagePaths):
        # load the input image and convert it from RGB (OpenCV ordering)
        # to dlib ordering (RGB)
        print("[INFO] processing image {}/{}".format(i + 1, len(imagePaths)))
        print(imagePath)
        image = cv2.imread(imagePath)
        try:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        except:
            continue
        # rgb = image
        # detect the (x, y)-coordinates of the bounding boxes
        # corresponding to each face in the input image
        if finder is None:
            boxes = face_recognition.face_locations(rgb, model="hog")
        elif isinstance(finder, FaceFinder):
            boxes = finder.detect_faces(rgb)
        else:
            raise Exception("Unknown type of face detector")
        # compute the facial embedding for the face
        if len(boxes) != 0:
            encodings = face_recognition.face_encodings(rgb, boxes)
            d = [{"imagePath": imagePath, "loc": box, "encoding": enc} for (box, enc) in zip(boxes, encodings)]
            data.extend(d)
    # dump the facial encodings data to disk
    print("[INFO] serializing encodings...")
    f = open(enc_path, "wb")
    f.write(pickle.dumps(data))
    f.close()
    return data

def encode_cluster_sf(path, enc_path):
    print("[INFO] quantifying faces...")
    imagePaths = list(paths.list_images(path))
    data = []
    # loop over the image paths
    for (i, imagePath) in enumerate(imagePaths):
        # load the input image and convert it from RGB (OpenCV ordering)
        # to dlib ordering (RGB)
        print("[INFO] processing image {}/{}".format(i + 1, len(imagePaths)))
        print(imagePath)
        image = cv2.imread(imagePath)
        try:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        except:
            continue

        boxes = [(0, rgb.shape[1]-1, rgb.shape[0]-1, 0)]
        encodings = face_recognition.face_encodings(rgb, boxes)
        d = [{"imagePath": imagePath, "loc": box, "encoding": enc} for (box, enc) in zip(boxes, encodings)]
        data.extend(d)
    # dump the facial encodings data to disk
    print("[INFO] serializing encodings...")
    f = open(enc_path, "wb")
    f.write(pickle.dumps(data))
    f.close()
    return data

