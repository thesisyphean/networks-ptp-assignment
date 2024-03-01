import socket
from threading import self, Thread
import threading
from enum import Enum
import logging

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class Command(Enum):
    ACCEPT_CONNECTION = 0
    SEND_USERNAME = 1
    ACCEPT_USERNAME = 2
    DECLINE_USERNAME = 3
    REQUEST_USER_LIST = 4
    REQUEST_PTP_CONNECTION = 5


class Client:
    def __init__(self, sock, server):
        self.sock = sock
        self.server = server

        self.username = ""
        self.available = False
        # not visible until specified as such
        self.visible = False
        self.busy = False

    def process_command(self, command_bytes):
        """
        takes input of command bytes
        1 byte for command type, 8 bytes for param 1, 2 bytes for param 2
        returns command for reply
        """
        command_type = command_bytes[0]
        # these indices are subject to change based on username length restrictions and encoding
        param_1 = command_bytes[1:9]
        param_2 = command_bytes[9:11]

        if command_type == Command.SEND_USERNAME.value:
            name = param_1.decode("utf-8")
            log.info(name)
            log.debug(self.server.users)

            if name in [n.username for n in self.server.users]:
                log.debug(f"Username ({name}) taken")
                return

            self.username = name
            self.available = True
            if int.from_bytes(param_2, "big") == 1:
                self.visible = True

                # send visible users list? May be simpler to just keep that as a separate
                # command and have the client side automatically request it on connection

            return self.send_command(Command.ACCEPT_USERNAME.value)

        elif command_type == Command.REQUEST_USER_LIST.value:
            pass
            # users = self.server.get_users()
            # generate data transfer message with user list and return

        elif command_type == Command.REQUEST_PTP_CONNECTION.value:
            pass

        # if statements for each other command the server could recieve

    def process_data_transfer(data_bytes):
        pass

    # this is fun lmao
    # pads params 1 and 2 with 0s by default, otherwise assumes values if inputed are padded
    def send_command(self, command_num, param_1=b"\x00" * 8, param_2=b"\x00" * 2):
        self.conn.sendall(b"\x01" + command_num.to_bytes(1, "big") + param_1 + param_2)

    def run(self):
        self.sock.listen()
        self.conn, self.addr = self.sock.accept()

        with self.conn:
            log.info(f"Connected by {self.addr}, Username: {self.username}")

            while True:
                initial_byte = self.conn.recv(1)
                if initial_byte[0] == 1:
                    # recieve rest of command
                    command_bytes = self.conn.recv(12)
                    self.process_command(command_bytes)

                else:
                    # process invalid message (server is never sent a data transfer)
                    pass

    def __str__(self):
        return f"User<{self.username}>"


class Server:
    # This IP adress is standard for the loopback interface
    # Only processes on the host will be able to connect to the server
    HOST = "127.0.0.1"
    PORT = 65432

    def __init__(self):
        self.sockets = []
        self._users_lock = threading.Lock()
        self._users: list[Client] = []

    @property
    def users(self):
        with self._users_lock:
            return self._users

    @users.setter
    def users(self, value):
        with self._users_lock:
            self._users = value

    def run(self):
        log.info("Server is running!")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.HOST, self.PORT))
            sock.listen()

            while True:
                conn, _ = sock.accept()

                new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                new_port = self.PORT + len(self.users) + 1
                new_sock.bind((self.HOST, new_port))
                conn.sendall(new_port.to_bytes(2, "little"))

                # Create a user connection instance and pass a reference to
                # the current state.
                user = Client(new_sock, self)
                self.users.append(user)

                # We don't need to track the thread lifecycle here
                Thread(target=user.run).start()

    def get_available_users(self):
        return ", ".join([user.username for user in self.users])


def main():
    server = Server()
    server.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Server stopped")
