import os
import socket
import time


class SimpleServer1(object):
    HOST, PORT = '', 8888

    def __init__(self):
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listen_socket.bind((self.HOST, self.PORT))
        self.listen_socket.listen(1)
        print 'Serving HTTP on port %s...' % self.PORT

    def serve_forever(self):
        while True:
            client_connection, client_address = self.listen_socket.accept()
            request = client_connection.recv(1023)
            print request

            http_response = """
            HTTP/1.1 200 OK
            Hello, World!"""

            client_connection.sendall(http_response)
            time.sleep(60)
            client_connection.close()


class SimpleServer2(object):
    SERVER_ADDRESS = (HOST, PORT) = '', 8888
    REQUEST_QUEUE_SIZE = 5

    def __init__(self):
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listen_socket.bind(self.SERVER_ADDRESS)
        self.listen_socket.listen(self.REQUEST_QUEUE_SIZE)
        print('Serving HTTP on port {port} ...'.format(port=self.PORT))
        print('Parent PID (PPID): {pid}n'.format(pid=os.getpid()))

    @staticmethod
    def handle_request(client_connection):
        request = client_connection.recv(1024)
        print(
            'Child PID: {pid}. Parent PID {ppid}'.format(
                pid=os.getpid(),
                ppid=os.getppid(),
            )
        )
        print(request.decode())
        http_response = b"""
        HTTP/1.1 200 OK

        Hello, World!
        """
        client_connection.sendall(http_response)
        time.sleep(60)

    def serve_forever(self):
        while True:
            client_connection, client_address = self.listen_socket.accept()
            pid = os.fork()
            if pid == 0:  # child
                self.listen_socket.close()  # close child copy
                self.handle_request(client_connection)
                client_connection.close()
                os._exit(0)  # child exits here
            else:  # parent
                client_connection.close()  # close parent copy and loop over

if __name__ == '__main__':
    server = SimpleServer2()
    server.serve_forever()



