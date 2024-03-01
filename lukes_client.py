import argparse
import socket
from enum import Enum
import logging
import struct
import random
from server import Command
from threading import Thread
import threading

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def pad_bytes(bytes, length):
    return bytes + b"\x00" * (length - len(bytes))


def ip_address_to_int(ip_address):
    return struct.unpack("!L", socket.inet_aton(ip_address))[0]


def int_to_ip_address(integer):
    return socket.inet_ntoa(struct.pack("!L", integer))


class Connection:
    def __init__(self, sock, client, username):
        self.sock = sock
        self.client = client
        self.username = username

    def run(self):
        log.debug(f"New thread connected to {self.username}")
        with self.sock:
            msg = "hooooowzit".encode("utf-8")
            self.sock.sendall(msg)
            # while True:
            data = self.sock.recv(10)
            print(data.decode())


class Client:
    def __init__(self, sock, vis):
        self.sock = sock
        self.visibility_preference = vis
        self.username = ""
        self.username_accepted = False
        self.ip_address = "127.0.0.1"
        self.connections = []

    def run(self):

        self.username = input("Please choose a username, max 8 bytes: ")
        # ensure username valid
        # pad username to 8 bytes

        self.send_command(Command.SEND_USERNAME.value, self.username.encode("utf-8"))

        while True:
            if self.sock.recv(1)[0] == 1:
                command_bytes = self.sock.recv(17)
                self.process_command(command_bytes)

            if not self.username_accepted:
                self.send_command(
                    Command.SEND_USERNAME.value, self.username.encode("utf-8")
                )

    # takes input of command bytes
    # 1 byte for command type, 8 bytes for param 1, 2 bytes for param 2
    # returns command for reply
    def process_command(self, command_bytes):
        log.debug(command_bytes)
        command_type = command_bytes[0]
        # these indices are subject to change based on username length restrictions and encoding
        param_1 = command_bytes[1:9]
        param_2 = command_bytes[9:18]

        if command_type == Command.ACCEPT_USERNAME.value:
            print("Username accepted")
            self.username_accepted = True
            if input("send connection request? ") == "yes":
                self.send_command(
                    Command.REQUEST_PTP_CONNECTION.value, "b".encode("utf-8")
                )

        elif command_type == Command.DECLINE_USERNAME.value:
            self.username = input(
                "This username is taken. Please choose another username: "
            )
        elif command_type == Command.RELAY_PTP_REQUEST.value:
            print(
                f"The user {param_1.decode()} has requested a peer to peer connection"
            )
            if input("Would you like to accept this connection? (yes/no): ") == "yes":
                ip = ip_address_to_int(self.ip_address)
                port = 10000 + random.randint(0, 10000)
                log.debug(f"Port: {port}, ip: {ip}")

                # create new socket and bind to new port
                new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                new_sock.bind((self.ip_address, port))

                log.debug(ip.to_bytes(4, "little") + port.to_bytes(2, "little"))
                # notify requesting client
                self.send_command(
                    Command.ACCEPT_PTP_CONNECTION.value,
                    param_1,
                    ip.to_bytes(4, "little") + port.to_bytes(2, "little"),
                )
                new_sock.listen()
                conn, addr = new_sock.accept()
                # Create a connection instance and pass a reference to
                # the current state.
                connection = Connection(conn, self, param_1.decode())
                self.connections.append(connection)

                Thread(target=connection.run).start()

            else:
                self.send_command(Command.DECLINE_PTP_CONNECTION.value, param_1)
        elif command_type == Command.USER_NOT_AVAILABLE.value:
            print("user not available")
        elif command_type == Command.DECLINE_PTP_CONNECTION.value:
            print(f"The user {param_1.decode()} has declined a peer to peer connection")

        elif command_type == Command.ACCEPT_PTP_CONNECTION.value:
            username = param_1.decode()
            log.debug(f"Acception recieved from {username}")
            ip_address = int_to_ip_address(int.from_bytes(param_2[:4], "little"))
            port = int.from_bytes(param_2[4:6], "little")

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((ip_address, port))
                connection = Connection(sock, self, username)

                self.connections.append(connection)

                Thread(target=connection.run).start()

    # pads params 1 and 2 with 0s by default, otherwise assumes values if inputed are padded
    def send_command(self, command_num, param_1=b"\x00" * 8, param_2=b"\x00" * 8):
        self.sock.sendall(
            b"\x01"
            + command_num.to_bytes(1, "little")
            + pad_bytes(param_1, 8)
            + pad_bytes(param_2, 8)
        )


def main():
    parser = argparse.ArgumentParser(prog="ChatApp", description="A ChatApp client")

    parser.add_argument(
        "-i",
        "--ip_address",
        default="127.0.0.1",
        help="The IP address of the server (127.0.0.1)",
    )

    parser.add_argument(
        "-p",
        "--port",
        default=65432,
        help="The port number of the server (65432)",
        type=int,
    )

    parser.add_argument(
        "-s",
        "--invisible",
        action="store_true",
        help="Whether to hide the user's username from other users (False)",
    )

    args = parser.parse_args()
    visibility_preference = False

    port = None
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((args.ip_address, args.port))
        print("Connected to the server!")
        port = int.from_bytes(sock.recv(2), "little")
        print(f"Port: {port}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((args.ip_address, port))
        client = Client(sock, visibility_preference)
        client.run()


if __name__ == "__main__":
    main()
