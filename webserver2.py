import socket
import StringIO
import sys
import os
import signal
import errno
import time


class WSGIServer(object):

    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    request_queue_size = 1

    def __init__(self, server_address):
        # Create a listening socket
        self.listen_socket = listen_socket = socket.socket(
            self.address_family,
            self.socket_type
        )
        # Allow to reuse the same address
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind
        listen_socket.bind(server_address)
        # Activate
        listen_socket.listen(self.request_queue_size)
        # Get server host name and port
        host, port = self.listen_socket.getsockname()[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port
        # Return headers set by Web framework/Web application
        self.headers_set = []

        self.client_connection = None
        self.request_data = None
        self.request_method = ''
        self.request_version = ''
        self.path = ''

        self.application = None

    def set_app(self, app):
        self.application = app

    @staticmethod
    def signal_handler(signum, frame):
        while True:
            try:
                # wait for completion of all child processes
                pid, status = os.waitpid(-1, os.WNOHANG)
            except OSError:
                return
            if pid == 0:
                return

    def serve_forever(self):
        # catch the child process exit signal and take action
        signal.signal(signal.SIGCHLD, self.signal_handler)

        while True:
            # New client connection
            try:
                self.client_connection, client_address = self.listen_socket.accept()
            except IOError as ex:
                code, msg = ex.args
                # parent process will be interrupted to deal with SIGCHLD signal
                # it can not accept request again
                # it will throw IOError with EINTR error code
                if code == errno.EINTR:
                    # cache the EINTR error code and re-accept request
                    continue
                else:
                    raise

            # Handle request concurrency
            pid = os.fork()
            if pid == 0:
                # child process
                # close the listen socket cause this is parent process's job
                self.listen_socket.close()
                self.handle_one_request()
                # child process exit
                os._exit(0)
            else:
                # parent process
                # close the copied client connection cause this is child process' job
                self.client_connection.close()

    def handle_one_request(self):
        self.request_data = request_data = self.client_connection.recv(1024)
        print "*"*50
        print request_data
        print "*"*50
        # Print formatted request data a la 'curl -v'
        print(''.join(
            '< {line}\n'.format(line=line)
            for line in request_data.splitlines()
        ))

        self.parse_request(request_data)

        # Construct environment dictionary using request data
        env = self.get_environ()

        # It's time to call our application callable and get
        # back a result that will become HTTP response body
        result = self.application(env, self.start_response)

        # Construct a response and send it back to the client
        self.finish_response(result)

    def parse_request(self, text):
        request_line = text.splitlines()[0]
        request_line = request_line.rstrip('\r\n')
        # Break down the request line into components
        (self.request_method,  # GET
         self.path,            # /hello
         self.request_version  # HTTP/1.1
         ) = request_line.split()

    def get_environ(self):
        env = dict()
        # Required WSGI variables
        env['wsgi.version'] = (1, 0)
        env['wsgi.url_scheme'] = 'http'
        env['wsgi.input'] = StringIO.StringIO(self.request_data)
        env['wsgi.errors'] = sys.stderr
        env['wsgi.multithread'] = False
        env['wsgi.multiprocess'] = False
        env['wsgi.run_once'] = False
        # Required CGI variables
        env['REQUEST_METHOD'] = self.request_method    # GET
        env['PATH_INFO'] = self.path              # /hello
        env['SERVER_NAME'] = self.server_name       # localhost
        env['SERVER_PORT'] = str(self.server_port)  # 8888
        return env

    def start_response(self, status, response_headers, exc_info=None):
        # Add necessary server headers
        server_headers = [
            ('Date', 'Tue, 31 Mar 2015 12:54:48 GMT'),
            ('Server', 'WSGIServer 0.2'),
        ]
        self.headers_set = [status, response_headers + server_headers]
        # To adhere to WSGI specification the start_response must return
        # a 'write' callable. We simplicity's sake we'll ignore that detail
        # for now.
        # return self.finish_response

    def finish_response(self, result):
        try:
            status, response_headers = self.headers_set
            response = 'HTTP/1.1 {status}\r\n'.format(status=status)
            for header in response_headers:
                response += '{0}: {1}\r\n'.format(*header)
            response += '\r\n'
            for data in result:
                response += data
            # Print formatted response data a la 'curl -v'
            print(''.join(
                '> {line}\n'.format(line=line)
                for line in response.splitlines()
            ))
            self.client_connection.sendall(response)
        finally:
            self.client_connection.close()
            time.sleep(30)


SERVER_ADDRESS = (HOST, PORT) = '', 8888


def make_server(server_address, app):
    server = WSGIServer(server_address)
    server.set_app(app)
    return server


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('Provide a WSGI application object as module:callable')
    app_path = sys.argv[1]
    module, application = app_path.split(':')
    module = __import__(module)
    application = getattr(module, application)
    httpd = make_server(SERVER_ADDRESS, application)
    print('WSGIServer: Serving HTTP on port {port} ...\n'.format(port=PORT))
    httpd.serve_forever()
