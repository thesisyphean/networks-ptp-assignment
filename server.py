import socket
import threading
from threading import Thread
from enum import Enum
import logging
import struct

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class Message(Enum):
    SIGN_UP = 0
    DECLINE_SIGN_UP = 1
    SIGN_IN = 2
    ACCEPT_SIGN_IN = 3
    DECLINE_SIGN_IN = 4
    REQUEST_USER_LIST = 5
    REQUEST_PTP_CONNECTION = 6
    USER_NOT_AVAILABLE = 7
    RELAY_PTP_REQUEST = 8
    DECLINE_PTP_CONNECTION = 9
    ACCEPT_PTP_CONNECTION = 10
    SIGN_OUT = 11

# 0 pads bytes object to specified length
def pad_bytes(bytes, length):
    return bytes + b"\x00" * (length - len(bytes))


class User:
    def __init__(self, sock, server):
        self.sock = sock
        self.server = server

        self.username = None
        self.password = None

        self.registered = False
        # Not visible until specified as such
        self.visible = False

    def process_command(self, command_bytes):
        """
        takes input of Message bytes
        1 byte for Message type, 8 bytes for param 1, 2 bytes for param 2
        returns Message for reply
        """
        command_type = command_bytes[0]
        # these indices are subject to change based on username length restrictions and encoding
        param_1 = command_bytes[1:9]
        param_2 = command_bytes[9:17]

        if command_type == Message.SIGN_UP.value:
            username = param_1.decode("utf-8")
            password = param_2.decode("utf-8")

            if username in self.server.registered_users:
                log.debug(f"Username '{username}' taken")
                self.send_command(Message.DECLINE_SIGN_UP.value)
                return

            self.username = username
            self.password = password
            self.registered = True
            self.server.add_registered_user(username, password)

            log.debug(f"Username '{username}' signed in")
            self.send_command(Message.ACCEPT_SIGN_IN.value)

        elif command_type == Message.SIGN_IN.value:
            username = param_1.decode("utf-8")
            password = param_2.decode("utf-8")

            # Decline login if username in list of registered users
            if username in [n.username for n in self.server.users]:
                # TODO: Error code enum?
                self.send_command(Message.DECLINE_SIGN_IN.value, 1)
                return

            registered_users = self.server.registered_users
            if username in registered_users and registered_users[username] == password:
                self.username = username
                self.password = password
                self.registered = True

                self.send_command(Message.ACCEPT_SIGN_IN.value)
                return

            self.send_command(Message.DECLINE_LOGIN.value)

        elif command_type == Message.REQUEST_USER_LIST.value:
            users = self.server.get_user_list()

            if len(users) == 0:
                data = ""
            else:
                data = (", ".join(self.server.get_user_list()))

            log.debug(f"Sending data transfer: {data}")
            self.send_data_transfer(True, 0, len(data), data.encode())

        elif command_type == Message.REQUEST_PTP_CONNECTION.value:
            username = param_1.decode("utf-8")
            user = self.server.get_user(username)

            if not user:
                log.debug(f"{username} not available")
                self.send_command(Message.USER_NOT_AVAILABLE.value)

            else:
                log.debug("Relay request")
                user.send_command(
                    Message.RELAY_PTP_REQUEST.value, self.username.encode(
                        "utf-8")
                )

        elif command_type == Message.DECLINE_PTP_CONNECTION.value:
            username = param_1.decode("utf-8")
            log.debug(username)
            user = self.server.get_user(username)
            # ensure user still connected
            if user:
                user.send_command(
                    Message.DECLINE_PTP_CONNECTION.value, self.username.encode(
                        "utf-8")
                )

        elif command_type == Message.ACCEPT_PTP_CONNECTION.value:
            username = param_1.decode("utf-8")
            connection_data = param_2
            user = self.server.get_user(username)

            user.send_command(
                Message.ACCEPT_PTP_CONNECTION.value,
                self.username.encode("utf-8"),
                connection_data,
            )

    # pads params 1 and 2 with 0s by default, otherwise assumes values if inputed are padded
    def send_command(self, Message_num, param_1=b"\x00" * 8, param_2=b"\x00" * 8):
        self.conn.sendall(
            b"\x01"
            + Message_num.to_bytes(1, "little")
            + pad_bytes(param_1, 8)
            + pad_bytes(param_2, 8)
        )

    def send_data_transfer(self, message, identifier_length, data_length, data):
        self.conn.sendall(
            (b"\x80"
            if message
            else b"\xc0")
            + identifier_length.to_bytes(1, "little")
            + data_length.to_bytes(4, "little")
            + data
        )

    # TODO Not entirely sure what's going on here, so just going to leave it
    def run(self):
        self.sock.listen()
        self.conn, self.addr = self.sock.accept()
        try:
            with self.conn:
                log.info(
                    f"Connected by {self.addr}, Username: {self.username}")

                while True:
                    initial_byte = self.conn.recv(1)
                    if initial_byte[0] == 1:
                        # recieve rest of Message
                        Message_bytes = self.conn.recv(17)
                        self.process_command(Message_bytes)

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
        self._users = []
        self.registered_users_lock = threading.Lock()
        self._registered_users = {}

    # TODO: How the fuck does this work???
    @property
    def users(self):
        with self.users_lock:
            return self._users

    @property
    def registered_users(self):
        with self.registered_users_lock:
            return self._registered_users

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

    def add_registered_user(self, username, password):
        with self.registered_users_lock:
            self._registered_users[username] = password

    def ip_address_to_int(ip_address):
        return struct.unpack("!L", socket.inet_aton(ip_address))[0]

    def int_to_ip_address(integer):
        return socket.inet_ntoa(struct.pack("!L", integer))

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
