from SocketServer import ThreadingUDPServer, BaseRequestHandler

class Stream(BaseRequestHandler):
    def __init__(self, *args, **kwargs):
        BaseRequestHandler.__init__(self, *args, **kwargs)

    def handle(self):
        data = self.request[0]
        socket = self.request[1]
        address = self.client_address[0]
        socket.sendto(data.upper(), address)


if __name__ == "__main__":
    HOST, PORT = "localhost", 5000

    server = ThreadingUDPServer((HOST, PORT), Stream)
    ip, port = server.server_address
    server.serve_forever()