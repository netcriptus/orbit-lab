import json
from SocketServer import ThreadingUDPServer, BaseRequestHandler

class Node(BaseRequestHandler):
    def __init__(self, *args, **kwargs):
        self.is_server = False
        self.translate_table = {}
        self.security_belt = []
        BaseRequestHandler.__init__(self, *args, **kwargs)
        
    def handle(self):
        self.address = self.server.server_address[0]
        data = self.request[0]
        socket = self.request[1]
        sender_address = self.client_address
        
        if "search" in data.split(" "):
            key = data.split(" ")[-1]
            if self.is_server:
                if key in self.translate_table:
                    socket.sendto(json.dumps(self.translate_table[key]), sender_address)
                elif self.security_belt:
                    #TODO: ask other servers
                    pass
                else:
                    socket.sendto(json.dumps([None]), sender_address)
            elif key == self.server.name:
                socket.sendto(json.dumps([self.address]), sender_address)

if __name__ == "__main__":
    HOST, PORT = "localhost", 5000

    server = ThreadingUDPServer((HOST, PORT), Node)
    server.name = "test"
    ip, port = server.server_address
    server.serve_forever()