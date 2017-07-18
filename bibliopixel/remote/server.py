from flask import Flask, jsonify, send_from_directory
from werkzeug.serving import run_simple
import threading
import queue
import os
import logging
from .. import log
import sys

if '--verbose' not in sys.argv:
    werk_log = logging.getLogger('werkzeug')
    werk_log.setLevel(logging.ERROR)


class RemoteServer:
    def __init__(self, q_send, q_recv):
        self.__server_thread = None
        self.__recv_thread = None
        cdir = os.path.dirname(os.path.realpath(__file__))
        static_dir = os.path.abspath(os.path.join(cdir, '../../ui/web_remote'))
        self.app = Flask('BP Remote', static_folder=static_dir)
        self._set_routes()
        self.q_send = q_send
        self.q_recv = q_recv

    def _set_routes(self):
        self.app.route('/')(self.index)
        self.app.route('/<path:path>')(self.static_files)
        self.app.route('/run_animation/<string:animation>')(self.run_animation)
        self.app.route('/stop')(self.stop_animation)
        self.app.route('/api/<string:request>')(self.api)
        self.app.route('/api/<string:request>/<data>')(self.api)

    def index(self):
        return self.app.send_static_file('index.html')

    def static_files(self, path):
        return self.app.send_static_file(path)

    def run_animation(self, animation):
        return self.api('run_animation', data=animation)

    def stop_animation(self):
        return self.api('stop_animation')

    def __get_resp(self):
        try:
            status, data = self.q_recv.get(timeout=5)
            return {
                'status': status,
                'msg': 'OK' if status else data,
                'data': data if status else None,
            }
        except queue.Empty:
            return {'status': False, 'msg': 'Timeout waiting for response.', 'data': None}

    def api(self, request, data=None):
        request = request.lower()
        self.q_send.put({'req': request, 'data': data})
        return jsonify(self.__get_resp())

    def run(self, external_access, port):
        host_ip = '0.0.0.0' if external_access else 'localhost'
        run_simple(host_ip, port, self.app, threaded=True)


def run_server(external_access, port, q_send, q_recv):
    server = RemoteServer(q_recv, q_send)
    local_url = 'Local: http://localhost:{}'.format(port)
    ext_url = 'External: http://<system_ip>:{}'.format(port)
    msg = 'Remote UI Server available at:\n' + local_url
    if external_access:
        msg += ('\n' + ext_url)
    log.info(msg)
    server.run(external_access, port)