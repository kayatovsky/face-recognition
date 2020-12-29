from flask import Flask
from flask_restful import Api, Resource
from bson.json_util import dumps
import datetime
import configparser
from user import Recording
app = Flask(__name__)
api = Api(app)


class config(Resource):
    def get(self, id=0):
        try:
            config = configparser.ConfigParser()
            config.read('config.ini')
            list = {}
            if id != 0:
                list = {'confidence_threshold': config[str(id)]['confidence_threshold'],
                        'top_k': config[str(id)]['top_k'],
                        'nms_threshold': config[str(id)]['nms_threshold'],
                        'keep_top_k': config[str(id)]['keep_top_k'],
                        'vis_thres': config[str(id)]['vis_thres'],
                        'network': config[str(id)]['network'],
                        'distance_threshold': config[str(id)]['distance_threshold'],
                        'samples': config[str(id)]['samples'],
                        'eps': config[str(id)]['eps'],
                        'fps_factor': config[str(id)]['fps_factor']
                        }
                return list, 200
            else:
                i = 1
                while i <= len(config.sections()) - 1:
                    list[i] = {'confidence_threshold': config[str(i)]['confidence_threshold'],
                               'top_k': config[str(i)]['top_k'],
                               'nms_threshold': config[str(i)]['nms_threshold'],
                               'keep_top_k': config[str(i)]['keep_top_k'],
                               'vis_thres': config[str(i)]['vis_thres'],
                               'network': config[str(i)]['network'],
                               'distance_threshold': config[str(i)]['distance_threshold'],
                               'samples': config[str(i)]['samples'],
                               'eps': config[str(i)]['eps'],
                               'fps_factor': config[str(i)]['fps_factor']
                               }
                    i += 1
                return list, 200
        except:
            return "Internal Server Error", 500

    def put(self, confidence_threshold, top_k, nms_threshold,
            keep_top_k, vis_thres, network,
            distance_threshold, samples, eps, fps_factor, id=0):
        try:
            config = configparser.ConfigParser()
            config.read('config.ini')
            if id == 0:
                id = len(config.sections())
            config[str(id)] = {'confidence_threshold': confidence_threshold,
                               'top_k': top_k,
                               'nms_threshold': nms_threshold,
                               'keep_top_k': keep_top_k,
                               'vis_thres': vis_thres,
                               'network': network,
                               'distance_threshold': distance_threshold,
                               'samples': samples,
                               'eps': eps,
                               'fps_factor': fps_factor
                               }
            with open('config.ini', 'w') as configfile:
                config.write(configfile)
            return id, 201
        except:
            return "Internal Server Error", 500

    def patch(self, id=0):
        try:
            config = configparser.ConfigParser()
            config.read('config.ini')
            if id == 0:
                return "Config not changed", 200
            else:
                config['ACTIVE'] = config[str(id)]
            with open('config.ini', 'w') as configfile:
                config.write(configfile)
            return 202
        except:
            return "Config not found", 404


class record(Resource):
    def get(self, room_num, date, time):
        try:
            date = datetime.datetime.strptime(date, '%Y-%m-%d')
            time = datetime.datetime.strptime(time, '%H:%M')
            rec = Recording.get(room_num, date, time)
            print(rec)
            if rec is None:
                return "Video not found", 404
            rec = rec.json
            return rec, 200
        except:
            return "Server error", 500


api.add_resource(config, '/config',
                 '/config/<int:id>',

                 '/config/<float:confidence_threshold>/<float:top_k>/<float:nms_threshold>/'
                 '<float:keep_top_k>/<float:vis_thres>/<string:network>/<float:distance_threshold>/'
                 '<float:samples>/<float:eps>/<float:fps_factor>')
api.add_resource(record, '/record/<string:room_num>/<string:date>/<string:time>')
if __name__ == "__main__":
    app.run(debug=True)
