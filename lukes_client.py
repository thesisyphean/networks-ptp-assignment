import argparse
import socket
from enum import Enum
import logging

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


# TODO: Cut these down
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


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


def colour(message, colour):
    return colour + message + Colors.END


# MAIN_MESSAGE = f"{colour("Welcome to ChatApp!", Colors.GREEN)}\n(1) List all users."


def pad_bytes(bytes, length):
    return bytes + b"\x00" * (length - len(bytes))


class Client:
    def __init__(self, sock, vis):
        self.sock = sock
        self.visibility_preference = vis
        self.username = ""
        self.username_accepted = False

    def run(self):

        self.username = input("Please choose a username, max 8 bytes: ")
        # ensure username valid
        # pad username to 8 bytes

        self.send_command(Command.SEND_USERNAME.value, self.username.encode("utf-8"))

        while True:
            if self.sock.recv(1)[0] == 1:
                command_bytes = self.sock.recv(12)
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
        param_2 = command_bytes[9:11]

        if command_type == Command.ACCEPT_USERNAME.value:
            print("Username accepted")
            self.username_accepted = True
            if input("send connection request? ") == "yes":
                self.send_command(
                    Command.REQUEST_PTP_CONNECTION.value, "bbbbbbbb".encode("utf-8")
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
                pass
            else:
                self.send_command(Command.DECLINE_PTP_CONNECTION.value, param_1)
        elif command_type == Command.USER_NOT_AVAILABLE.value:
            print("user not available")
        elif command_type == Command.DECLINE_PTP_CONNECTION.value:
            print(f"The user {param_1.decode()} has declined a peer to peer connection")

    # pads params 1 and 2 with 0s by default, otherwise assumes values if inputed are padded
    def send_command(self, command_num, param_1=b"\x00" * 8, param_2=b"\x00" * 2):
        self.sock.sendall(
            b"\x01"
            + command_num.to_bytes(1, "big")
            + pad_bytes(param_1, 8)
            + pad_bytes(param_2, 2)
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
