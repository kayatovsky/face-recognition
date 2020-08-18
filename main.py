from rofl import ROFL
from recognizer import Recognizer
from encode import encode_cluster_sf
import api

model = "trained_knn_model.clf"
# recog = Recognizer()
# recog.train(n_neighbors=2, model_save_path=model)

# rofl = ROFL(recognizer_path=model, retina=True, on_gpu=True, emotions=True)
filename = "jackle.mp4"
filename1 = "twice.mp4"
api.upload_video("video_output/2020-08-12_08-00_305_54.mp4", upload_name="2020-08-12_08:00_305.mp4",
                 folder_id="1iR8EpBv0jGPwVQ7YepeFPccj4a0jhzPJ")

# rofl.basic_run(".", filename1, fps_factor=30, recognize=True, emotions=True)
# rofl.run_emotions(".", filename1, fps_factor=30)
# rofl.basic_run(".", filename, fps_factor=30)
# rofl.run_and_remember_strangers(filename, fps_factor=30)

# encode_cluster_sf("./strangers", "./enc_cluster.pickle")
# rofl.clust.remember_strangers("enc_cluster.pickle", save_path="known_faces")
