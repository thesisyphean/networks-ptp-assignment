import socket
import threading
from threading import Thread
from enum import Enum
import logging
import struct

log = logging.getLogger("server")
logging.basicConfig(level=logging.INFO)


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
    ALREADY_LOGGED_IN = 12

def pad_bytes(bytes, length):
    """Left pad bytes with null bytes"""
    return bytes + b"\x00" * (length - len(bytes))


class User:
    """Manages a connection to a specific client"""
    def __init__(self, sock, server):
        """Takes a TCP socket and a reference"""
        self.sock = sock
        self.server = server

        self.username = None
        self.password = None

        self.registered = False
        # Not visible until specified as such
        self.visible = False

    def process_command(self, command_bytes):
        """
        Takes command bytes
        1 byte for command type, 8 bytes for param 1, 8 bytes for param 2
        """
        # The protocol specification is described in the report
        command_type = command_bytes[0]
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

            # Decline login if username in list of current users
            if username in [n.username for n in self.server.users]:
                self.send_command(Message.ALREADY_LOGGED_IN.value)
                return

            # Confirm correct username and password match
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
                data = (", ".join(users))

            log.debug(f"Sending data transfer: {data}")
            self.send_data_transfer(True, 0, len(data), data.encode())

        elif command_type == Message.REQUEST_PTP_CONNECTION.value:
            username = param_1.decode("utf-8")
            user = self.server.get_user(username)

            # User has already signed out
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
            # Ensure user is still connected
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

    def send_command(self, command_num, param_1=b"\x00" * 8, param_2=b"\x00" * 8):
        """Pads params 1 and 2 with 0s by default, otherwise assumes values if inputed are padded"""
        self.conn.sendall(
            b"\x01"
            + command_num.to_bytes(1, "little")
            + pad_bytes(param_1, 8)
            + pad_bytes(param_2, 8)
        )

    def send_data_transfer(self, message, identifier_length, data_length, data):
        """Sends data transfer, assuming data is encoded"""
        self.conn.sendall(
            (b"\x00"
            if message
            else b"\x40")
            + identifier_length.to_bytes(1, "little")
            + data_length.to_bytes(4, "little")
            + data
        )

    def run(self):
        """Waits for requests from the client, handling exceptions were possible"""
        self.sock.listen()
        self.conn, self.addr = self.sock.accept()
        with self.conn:
            log.info(f"Connected by {self.addr}")

            while True:
                try:
                    initial_byte = self.conn.recv(1)
                except:
                    log.debug("Connection forcibly closed")
                    self.server.remove_user(self)
                    break

                # The connection was closed without signout by the client
                if initial_byte == b"":
                    log.debug("Connection closed")
                    self.server.remove_user(self)
                    break

                if initial_byte[0] == 1:
                    # Recieve rest of message
                    command_bytes = self.conn.recv(17)
                    self.process_command(command_bytes)

                # The server is *never* sent a data transfer by the client
                # This is assumed to be malicious
                else:
                    log.debug("Data transfer received, closing connection")
                    self.server.remove_user(self)
                    break


class Server:
    """The main server instance that manages shared state for the application"""
    # This IP adress is standard for the loopback interface
    # Only processes on the host will be able to connect to the server
    HOST = "127.0.0.1"
    PORT = 65432

    def __init__(self):
        self.sockets = []
        self.users_lock = threading.Lock()
        # List of usernames
        self._users = []
        self.registered_users_lock = threading.Lock()
        # Dictionary with username/password pairs
        self._registered_users = {}

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
        """Filters any errors from the user list"""
        return list(filter(None, [user.username for user in self.users]))

    def remove_user(self, username):
        for i in range(len(self.users)):
            if self.users[i].username == username:
                self.users.pop(i)
                return

    def add_registered_user(self, username, password):
        with self.registered_users_lock:
            self._registered_users[username] = password

    def ip_address_to_int(ip_address):
        """Converts an ip address to an int to be sent over a socket"""
        return struct.unpack("!L", socket.inet_aton(ip_address))[0]

    def int_to_ip_address(integer):
        """Converts an int to a ip address to be received over a socket"""
        return socket.inet_ntoa(struct.pack("!L", integer))

    def run(self):
        log.info("Server is running!")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.HOST, self.PORT))
            sock.listen()

            while True:
                conn, _ = sock.accept()

                # Create a new socket to handle the connection
                new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                new_port = self.PORT + len(self.users) + 1
                new_sock.bind((self.HOST, new_port))
                # Send the new port so it can reconnect
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
