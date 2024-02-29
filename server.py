import socket
from threading import Thread
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
    USER_NOT_AVAILABLE = 6
    RELAY_PTP_REQUEST = 7
    DECLINE_PTP_CONNECTION = 8


# 0 pads bytes object to specified length
def pad_bytes(bytes, length):
    return bytes + b"\x00" * (length - len(bytes))


class User:
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
                self.send_command(Command.DECLINE_USERNAME.value)
                return

            self.username = name
            self.available = True
            if int.from_bytes(param_2, "big") == 1:
                self.visible = True

                # send visible users list? May be simpler to just keep that as a separate
                # command and have the client side automatically request it on connection
            self.send_command(Command.ACCEPT_USERNAME.value)
            return

        elif command_type == Command.REQUEST_USER_LIST.value:
            pass
            # users = self.server.get_users()
            # generate data transfer message with user list and return

        elif command_type == Command.REQUEST_PTP_CONNECTION.value:
            username = param_1.decode("utf-8")
            log.debug(username)
            user = self.server.get_user(username)
            if not user:
                log.debug("not available")
                self.send_command(Command.USER_NOT_AVAILABLE.value)
                pass
            else:
                log.debug("relay request")
                user.send_command(
                    Command.RELAY_PTP_REQUEST.value, self.username.encode("utf-8")
                )
        elif command_type == Command.DECLINE_PTP_CONNECTION.value:
            username = param_1.decode("utf-8")
            log.debug(username)
            user = self.server.get_user(username)
            # ensure user still connected
            if user:
                user.send_command(
                    Command.DECLINE_PTP_CONNECTION.value, self.username.encode("utf-8")
                )

        # if statements for each other command the server could recieve

    def process_data_transfer(data_bytes):
        pass

    # pads params 1 and 2 with 0s by default, otherwise assumes values if inputed are padded
    def send_command(self, command_num, param_1=b"\x00" * 8, param_2=b"\x00" * 2):
        self.conn.sendall(
            b"\x01"
            + command_num.to_bytes(1, "big")
            + pad_bytes(param_1, 8)
            + pad_bytes(param_2, 2)
        )

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


class Server:
    # This IP adress is standard for the loopback interface
    # Only processes on the host will be able to connect to the server
    HOST = "127.0.0.1"
    PORT = 65432

    def __init__(self):
        self.sockets = []
        self.users_lock = threading.Lock()
        self._users: list[User] = []

    @property
    def users(self):
        with self.users_lock:
            return self._users

    @users.setter
    def users(self, value):
        with self.users_lock:
            self._users = value

    # def send_command_to_user(self, username, command_num, param_1, param_2):
    #     with self._users_lock:
    #         for user in self.users:
    #             if user.username == username:
    #                 user.send_command(command_num, param_1, param_2)

    def get_user(self, username):
        with self.users_lock:
            for user in self._users:
                log.debug(user.username)
                if user.username == username:
                    return user
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
