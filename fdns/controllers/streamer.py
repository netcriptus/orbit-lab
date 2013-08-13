from SocketServer import ThreadingUDPServer, BaseRequestHandler

class Stream(BaseRequestHandler):
    def __init__(self, *args, **kwargs):
        self.log = open("simulation_log.txt", "a+")
        BaseRequestHandler.__init__(self, *args, **kwargs)

    def handle(self):
        data = self.request[0]
        socket = self.request[1]
        self.log.write("{} wrote: ".format(self.client_address[0]))
        self.log.write(data)
        socket.sendto(data.upper(), self.client_address)


if __name__ == "__main__":
    HOST, PORT = "localhost", 5000

    server = ThreadingUDPServer((HOST, PORT), Stream)
    ip, port = server.server_address
    server.serve_forever()