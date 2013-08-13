import sys
import os
sys.path.insert(0, os.path.abspath('../..'))

from controllers.streamer import Stream
from SocketServer import ThreadingUDPServer

HOST, PORT = "localhost", 5000

server = ThreadingUDPServer((HOST, PORT), Stream)
server.serve_forever()