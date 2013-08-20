#!/usr/bin/python


import sys
import os
sys.path.insert(0, os.path.abspath('../..'))

from controllers.streamer import Stream
from SocketServer import ThreadingUDPServer

HOST, PORT = "0.0.0.0", 5000

server = ThreadingUDPServer((HOST, PORT), Stream)
server.serve_forever()