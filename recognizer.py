import math
from sklearn import neighbors
import os
import os.path
import pickle
from PIL import Image, ImageDraw
import face_recognition
from face_recognition.face_recognition_cli import image_files_in_folder
from face_finder import FaceFinder


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


class Recognizer:

    def __init__(self, finder=None):
        self.finder = finder
        self.knn = None

    def train(self, train_dir="./known_faces", model_save_path=None, n_neighbors=None, knn_algo='ball_tree', verbose=False):
        """
        Trains a k-nearest neighbors classifier for face recognition.
        :param train_dir: directory that contains a sub-directory for each known person, with its name.
         (View in source code to see train_dir example tree structure)
         Structure:
            <train_dir>/
            ├── <person1>/
            │   ├── <somename1>.jpeg
            │   ├── <somename2>.jpeg
            │   ├── ...
            ├── <person2>/
            │   ├── <somename1>.jpeg
            │   └── <somename2>.jpeg
            └── ...
        :param model_save_path: (optional) path to save model on disk
        :param n_neighbors: (optional) number of neighbors to weigh in classification. Chosen automatically if not specified
        :param knn_algo: (optional) underlying data structure to support knn.default is ball_tree
        :param verbose: verbosity of training
        :return: returns knn classifier that was trained on the given data.
        """
        X = []
        y = []

        # Loop through each person in the training set
        for class_dir in os.listdir(train_dir):
            if not os.path.isdir(os.path.join(train_dir, class_dir)):
                continue

            # Loop through each training image for the current person
            for img_path in image_files_in_folder(os.path.join(train_dir, class_dir)):
                image = face_recognition.load_image_file(img_path)
                # if self.finder is None:
                #     face_bounding_boxes = face_recognition.face_locations(image)
                # elif isinstance(self.finder, FaceFinder):
                #     face_bounding_boxes = self.finder.detect_faces(image)
                # else:
                #     raise Exception("Unknown type of face detector")
                face_bounding_boxes = face_recognition.face_locations(image)

                if len(face_bounding_boxes) != 1:
                    # If there are no people (or too many people) in a training image, skip the image.
                    if verbose:
                        print("Image {} not suitable for training: {}".format(img_path,
                                                                              "Didn't find a face"
                                                                              if len(face_bounding_boxes) < 1
                                                                              else "Found more than one face"))
                else:
                    # Add face encoding for current image to the training set
                    X.append(face_recognition.face_encodings(image, known_face_locations=face_bounding_boxes)[0])
                    y.append(class_dir)

        # Determine how many neighbors to use for weighting in the KNN classifier
        if n_neighbors is None:
            n_neighbors = int(round(math.sqrt(len(X))))
            if verbose:
                print("Chose n_neighbors automatically:", n_neighbors)

        enc = {"encodings": X, "names": y}
        print("[INFO] serializing encodings...")
        f = open(train_dir + "/enc_cls.pickle", "wb")
        f.write(pickle.dumps(enc))
        f.close()

        # Create and train the KNN classifier
        knn_clf = neighbors.KNeighborsClassifier(n_neighbors=n_neighbors, algorithm=knn_algo, weights='distance')
        knn_clf.fit(X, y)

        # Save the trained KNN classifier
        if model_save_path is not None:
            with open(model_save_path, 'wb') as f:
                pickle.dump(knn_clf, f)

        self.knn = knn_clf

        return knn_clf

    def load_model(self, path):
        with open(path, 'rb') as f:
            self.knn = pickle.load(f)

    def predict(self, x_img, distance_threshold=0.6, X_face_locations=None):
        """
        Recognizes faces in given image using a trained KNN classifier
        :param x_img: image to be recognized as ndarray
        :param distance_threshold: (optional) distance threshold for face classification. the larger it is,
            the more chance of mis-classifying an unknown person as a known one.
        :return: a list of names and face locations for the recognized faces in the image: [(name, bounding box), ...].
            For faces of unrecognized persons, the name 'unknown' will be returned.
        """

        # Load a trained KNN model (if one was passed in)
        if self.knn is None:
            raise Exception("Load KNN model before recognizing")

        # Load image file and find face locations
        if X_face_locations is None:
            if self.finder is None:
                X_face_locations = face_recognition.face_locations(x_img)
            elif isinstance(self.finder, FaceFinder):
                X_face_locations = self.finder.detect_faces(x_img)
            else:
                raise Exception("Unknown type of face detector")

        # If no faces are found in the image, return an empty result.
        if len(X_face_locations) == 0:
            return []

        # Find encodings for faces in the test image
        faces_encodings = face_recognition.face_encodings(x_img, known_face_locations=X_face_locations)

        # Use the KNN model to find the best matches for the test face
        closest_distances = self.knn.kneighbors(faces_encodings, n_neighbors=1)
        are_matches = [closest_distances[0][i][0] <= distance_threshold for i in range(len(X_face_locations))]

        # Predict classes and remove classifications that aren't within the threshold
        return [(pred, loc) if rec else ("unknown", loc) for pred, loc, rec in zip(self.knn.predict(faces_encodings),
                                                                                   X_face_locations, are_matches)]


def show_prediction_labels_on_image(img, predictions):
    """
    Shows the face recognition results visually.
    :param img: path to image to be recognized
    :param predictions: results of the predict function
    :return:
    """
    try:
        pil_image = Image.open(img).convert("RGB")
    except:
        pil_image = Image.fromarray(img)
    draw = ImageDraw.Draw(pil_image)

    for name, (top, right, bottom, left) in predictions:
        # Draw a box around the face using the Pillow module
        draw.rectangle(((left, top), (right, bottom)), outline=(0, 0, 255))

        # There's a bug in Pillow where it blows up with non-UTF-8 text
        # when using the default bitmap font
        name = name.encode("UTF-8")

        # Draw a label with a name below the face
        text_width, text_height = draw.textsize(name)
        draw.rectangle(((left, bottom - text_height - 10), (right, bottom)), fill=(0, 0, 255), outline=(0, 0, 255))
        draw.text((left + 6, bottom - text_height - 5), name, fill=(255, 255, 255, 255))

    # Remove the drawing library from memory as per the Pillow docs
    del draw

    # Display the resulting image
    pil_image.show()
