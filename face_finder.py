from __future__ import print_function
# import argparse
import torch.backends.cudnn as cudnn
from data import cfg_mnet, cfg_re50
from layers.functions.prior_box import PriorBox
from utils.nms.py_cpu_nms import py_cpu_nms
from models.retinaface import RetinaFace
from utils.box_utils import decode, decode_landm
import time
import numpy as np
import torch


class FaceFinder:
    def __init__(self, on_gpu=False,
                 confidence_threshold=0.02,
                 top_k=5000,
                 nms_threshold=0.4,
                 keep_top_k=750,
                 vis_thres=0.6,
                 network='resnet50'):
        self.on_gpu = on_gpu

        # from classifier by Sizykh Ivan

        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

        self.network = network
        self.cpu = False
        self.confidence_threshold = confidence_threshold
        self.top_k = top_k
        self.nms_threshold = nms_threshold
        self.keep_top_k = keep_top_k
        self.vis_thres = vis_thres
        if network == 'resnet50':
            self.trained_model = './weights/Resnet50_Final.pth'
        else:
            self.trained_model = './weights/mobilenet0.25_Final.pth'
        self.resize = 1

        torch.set_grad_enabled(False)
        cfg = None
        if self.network == "mobile0.25":
            cfg = cfg_mnet
        elif self.network == "resnet50":
            cfg = cfg_re50
        # cfg = cfg_re50
        # net and model
        detector = RetinaFace(cfg=cfg, phase='test')
        detector = self.load_model(model=detector, pretrained_path=self.trained_model,
                                   load_to_cpu=self.cpu)
        detector.eval()
        print('Finished loading model!')
        # print(detector)

        if self.on_gpu:
            cudnn.benchmark = True
            self.detector = detector.to(self.device)
        else:
            self.detector = detector
        self.cfg = cfg

    def load_model(self, model, pretrained_path, load_to_cpu):
        """load model of RetinaFace for face detection"""
        def remove_prefix(state_dict, prefix):
            ''' Old style model is stored with all names of parameters sharing common prefix 'module.' '''
            print('remove prefix \'{}\''.format(prefix))
            f = lambda x: x.split(prefix, 1)[-1] if x.startswith(prefix) else x
            return {f(key): value for key, value in state_dict.items()}

        def check_keys(model, pretrained_state_dict):
            ckpt_keys = set(pretrained_state_dict.keys())
            model_keys = set(model.state_dict().keys())
            used_pretrained_keys = model_keys & ckpt_keys
            unused_pretrained_keys = ckpt_keys - model_keys
            missing_keys = model_keys - ckpt_keys
            print('Missing keys:{}'.format(len(missing_keys)))
            print('Unused checkpoint keys:{}'.format(len(unused_pretrained_keys)))
            print('Used keys:{}'.format(len(used_pretrained_keys)))
            assert len(used_pretrained_keys) > 0, 'load NONE from pretrained checkpoint'
            return True

        print('Loading pretrained model from {}'.format(pretrained_path))
        if load_to_cpu:
            pretrained_dict = torch.load(pretrained_path, map_location=lambda storage, loc: storage)
        else:
            if self.on_gpu:
                device = torch.cuda.current_device()
                pretrained_dict = torch.load(pretrained_path, map_location=lambda storage, location: storage.cuda(device))
            else:
                pretrained_dict = torch.load(pretrained_path, map_location=lambda storage, location: storage)
        if "state_dict" in pretrained_dict.keys():
            pretrained_dict = remove_prefix(pretrained_dict['state_dict'], 'module.')
        else:
            pretrained_dict = remove_prefix(pretrained_dict, 'module.')
        check_keys(model, pretrained_dict)
        model.load_state_dict(pretrained_dict, strict=False)
        return model

    def detect_faces(self, img_raw):

        img = np.float32(img_raw)

        im_height, im_width, _ = img.shape
        scale = torch.Tensor([img.shape[1], img.shape[0], img.shape[1], img.shape[0]])
        img -= (104, 117, 123)
        img = img.transpose(2, 0, 1)
        img = torch.from_numpy(img).unsqueeze(0)
        if self.on_gpu:
            img = img.to(self.device)
            scale = scale.to(self.device)
        # graph = 0
        tic = time.time()
        loc, conf, landms = self.detector(img)  # forward pass
        print('net forward time: {:.4f}'.format(time.time() - tic))

        priorbox = PriorBox(self.cfg, image_size=(im_height, im_width))
        priors = priorbox.forward()
        if self.on_gpu:
            priors = priors.to(self.device)
        prior_data = priors.data
        boxes = decode(loc.data.squeeze(0), prior_data, self.cfg['variance'])
        boxes = boxes * scale / self.resize
        boxes = boxes.cpu().numpy()
        scores = conf.squeeze(0).data.cpu().numpy()[:, 1]
        landms = decode_landm(landms.data.squeeze(0), prior_data, self.cfg['variance'])
        scale1 = torch.Tensor([img.shape[3], img.shape[2], img.shape[3], img.shape[2],
                               img.shape[3], img.shape[2], img.shape[3], img.shape[2],
                               img.shape[3], img.shape[2]])
        if self.on_gpu:
            scale1 = scale1.to(self.device)
        landms = landms * scale1 / self.resize
        landms = landms.cpu().numpy()

        # ignore low scores
        inds = np.where(scores > self.confidence_threshold)[0]
        boxes = boxes[inds]
        landms = landms[inds]
        scores = scores[inds]

        # keep top-K before NMS
        order = scores.argsort()[::-1][:self.top_k]
        boxes = boxes[order]
        landms = landms[order]
        scores = scores[order]

        # do NMS
        dets = np.hstack((boxes, scores[:, np.newaxis])).astype(np.float32, copy=False)
        keep = py_cpu_nms(dets, self.nms_threshold)
        dets = dets[keep, :]
        landms = landms[keep]

        # keep top-K faster NMS
        dets = dets[:self.keep_top_k, :]
        landms = landms[:self.keep_top_k, :]

        dets = np.concatenate((dets, landms), axis=1)

        faces = []
        for f in dets:
            # fr: top, right, bottom, left
            # retina: left, right, bottom, top
            faces.append((int(f[1]), int(f[2]), int(f[3]), int(f[0])))

        return faces
        # parser = argparse.ArgumentParser(description='Retinaface')
        # device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        #
        # parser.add_argument('-m', '--trained_model', default='./weights/Resnet50_Final.pth',
        #                     type=str, help='Trained state_dict file path to open')
        # parser.add_argument('--network', default='resnet50', help='Backbone network mobile0.25 or resnet50')
        # # parser.add_argument('--cpu', action="store_true", default=False, help='Use cpu inference')
        # parser.add_argument('--cpu', action="store_true", default=False, help='Use cpu inference')
        # parser.add_argument('--confidence_threshold', default=0.02, type=float, help='confidence_threshold')
        # parser.add_argument('--top_k', default=5000, type=int, help='top_k')
        # parser.add_argument('--nms_threshold', default=0.4, type=float, help='nms_threshold')
        # parser.add_argument('--keep_top_k', default=750, type=int, help='keep_top_k')
        # parser.add_argument('-s', '--save_image', action="store_true", default=True, help='show detection results')
        # parser.add_argument('--vis_thres', default=0.6, type=float, help='visualization_threshold')
        #
        # parser.add_argument('-v', '--video', default='vid.mp4', type=str)
        #
        # args = parser.parse_args()
