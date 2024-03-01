import socket
from threading import self, Thread
import threading
from enum import Enum
import logging
import struct

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class Command(Enum):
    ACCEPT_CONNECTION = 0
    # SEND_USERNAME = 1
    # ACCEPT_USERNAME = 2
    # DECLINE_USERNAME = 3
    REQUEST_USER_LIST = 4
    REQUEST_PTP_CONNECTION = 6
    USER_NOT_AVAILABLE = 7
    RELAY_PTP_REQUEST = 8
    DECLINE_PTP_CONNECTION = 9
    ACCEPT_PTP_CONNECTION = 10
    REGISTER = 11
    DECLINE_REGISTER = 12
    LOGIN = 13
    DECLINE_LOGIN = 14
    ALREADY_LOGGED_IN = 15
    ACCEPT_LOGIN = 16


def ip_address_to_int(ip_address):
    return struct.unpack("!L", socket.inet_aton(ip_address))[0]


def int_to_ip_address(integer):
    return socket.inet_ntoa(struct.pack("!L", integer))


# 0 pads bytes object to specified length
def pad_bytes(bytes, length):
    return bytes + b"\x00" * (length - len(bytes))


class User:
    def __init__(self, sock, server):
        self.sock = sock
        self.server = server

        self.username = ""
        self.password = ""
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
        param_2 = command_bytes[9:17]

        if command_type == Command.REGISTER.value:
            name = param_1.decode("utf-8")
            password = param_2.decode("utf-8")

            if name in [n[0] for n in self.server.registered_users]:
                log.debug(f"Username ({name}) taken")
                self.send_command(Command.DECLINE_REGISTER.value)
                return

            self.username = name
            self.password = password
            self.available = True
            self.server.add_registered_user((name, password))

            self.send_command(Command.ACCEPT_LOGIN.value, name.encode("utf-8"))
            return

        elif command_type == Command.LOGIN.value:
            name = param_1.decode("utf-8")
            password = param_2.decode("utf-8")
            log.info(name)
            log.debug(self.server.users)

            # Decline login if username in list of online users
            if name in [n.username for n in self.server.users]:
                self.send_command(Command.ALREADY_LOGGED_IN.value)
                return

            elif (name, password) in self.server.registered_users:
                self.username = name
                self.available = True
                self.send_command(Command.ACCEPT_LOGIN.value, name.encode("utf-8"))
                return

            self.send_command(Command.DECLINE_LOGIN.value)

        elif command_type == Command.REQUEST_USER_LIST.value:
            data = (", ".join(self.server.get_user_list())).encode("utf-8")
            self.send_data_transfer(Command.SEND_USER_LIST.value, 0, len(data), data)
            return

        elif command_type == Command.REQUEST_PTP_CONNECTION.value:
            username = param_1.decode("utf-8")
            log.debug(username)
            user = self.server.get_user(username)
            if not user:
                log.debug("not available")
                self.send_command(Command.USER_NOT_AVAILABLE.value)
                return
            else:
                log.debug("relay request")
                user.send_command(
                    Command.RELAY_PTP_REQUEST.value, self.username.encode("utf-8")
                )
                return

        elif command_type == Command.DECLINE_PTP_CONNECTION.value:
            username = param_1.decode("utf-8")
            log.debug(username)
            user = self.server.get_user(username)
            # ensure user still connected
            if user:
                user.send_command(
                    Command.DECLINE_PTP_CONNECTION.value, self.username.encode("utf-8")
                )
                return

        elif command_type == Command.ACCEPT_PTP_CONNECTION.value:
            username = param_1.decode("utf-8")
            connection_data = param_2
            user = self.server.get_user(username)

            user.send_command(
                Command.ACCEPT_PTP_CONNECTION.value,
                self.username.encode("utf-8"),
                connection_data,
            )

        # if statements for each other command the server could recieve

    # pads params 1 and 2 with 0s by default, otherwise assumes values if inputed are padded
    def send_command(self, command_num, param_1=b"\x00" * 8, param_2=b"\x00" * 8):
        self.conn.sendall(
            b"\x01"
            # TODO: Maybe give this a test?
            + command_num.to_bytes(1, "little")
            + pad_bytes(param_1, 8)
            + pad_bytes(param_2, 8)
        )

    def send_data_transfer(self, message, identifier_length, data_length, data):
        self.conn.sendall(
            b"\x80"
            if message
            else b"\xc0"
            # TODO: Same here
            + identifier_length.to_bytes(1, "little")
            + data_length.to_bytes(4, "little")
            + data
        )

    def run(self):
        self.sock.listen()
        self.conn, self.addr = self.sock.accept()
        try:
            with self.conn:
                log.info(f"Connected by {self.addr}, Username: {self.username}")

                while True:
                    initial_byte = self.conn.recv(1)
                    if initial_byte[0] == 1:
                        # recieve rest of command
                        command_bytes = self.conn.recv(17)
                        self.process_command(command_bytes)

                    else:
                        # process invalid message (server is never sent a data transfer)
                        pass
        # TODO
        # doesn't work cause of with statement :(
        except ():
            log.debug("Socked closed")
            self.server.remove_user(self)


class Server:
    # This IP adress is standard for the loopback interface
    # Only processes on the host will be able to connect to the server
    HOST = "127.0.0.1"
    PORT = 65432

    def __init__(self):
        self.sockets = []
        self.users_lock = threading.Lock()
        # TODO manage users closing connection and remove them from user list (not registered users though)
        self._users = []
        self._registered_users_lock = threading.Lock()
        # list of tuples: (username, password)
        self._registered_users = []

    @property
    def users(self):
        with self.users_lock:
            return self._users

    @users.setter
    def users(self, value):
        with self.users_lock:
            self._users = value

    @property
    def registered_users(self):
        with self._registered_users_lock:
            return self._registered_users

    def add_registered_user(self, username):
        with self._registered_users_lock:
            self._registered_users.append(username)

    def get_user(self, username):
        for user in self.users:
            log.debug(user.username)
            if user.username == username:
                return user

    def get_user_list(self):
        return [user.username for user in self.users]

    def remove_user(self, username):
        for user in self.users:
            if user.username == username:
                self.users.remove(user)
                return

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
                user = User(new_sock, self)
                self.users.append(user)

                Thread(target=user.run).start()


def main():
    server = Server()
    server.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Server stopped")
