import argparse
import socket
from server import Message
import textwrap
import struct
import random

# These have been pulled from the Blender build scripts
# Terminal colours are changed by inserting the escape sequence
#  into the string before the text and following it with the
#  end escape sequence


class Colours:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    def coloured(message, colour):
        return colour + message + Colours.END

MESSAGE_BYTE_COUNT = 18

def pad_bytes(bytes, length):
    return bytes + b"\x00" * (length - len(bytes))

def ip_address_to_int(ip_address):
    return struct.unpack("!L", socket.inet_aton(ip_address))[0]

def int_to_ip_address(integer):
    return socket.inet_ntoa(struct.pack("!L", integer))


class Client:
    def __init__(self, args):
        self.username = args.username
        self.server_ip_address = args.ip_address
        self.server_port = args.port
        self.signed_up = args.signin

        self.ptp_requests = []

    def command(self, command_type, param_1=b"\x00" * 8, param_2=b"\x00" * 8):
        self.server.sendall(
            b"\x01" +
            command_type.to_bytes(1, "little") +
            pad_bytes(param_1, 8) +
            pad_bytes(param_2, 8)
        )

    def run(self):
        # Create and bind the server socket
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.connect((self.server_ip_address, self.server_port))
        # This ensures that the socket can be used with coroutines
        # self.server.setblocking(False)

        # Get the personal socket that the server will use
        self.server_port = int.from_bytes(self.server.recv(2), "little")
        self.server.close()

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.connect((self.server_ip_address, self.server_port))

        # The first step is to sign up or sign in
        if self.signed_up:
            self.sign_in()
        else:
            self.sign_up()

        while True:
            print(textwrap.dedent("""\
                  You can:
                  (1) Request the user list
                  (2) Request a PTP connection
                  (3) Accept a PTP connection
                  (4) Enter an active chat
                  (5) Sign out from the server
                  Please enter your choice as a number:"""))

            choice = input()
            if not choice.isdecimal():
                continue

            choice = int(choice)
            match choice:
                case 1:
                    self.request_user_list()
                case 2:
                    self.request_ptp_connection()
                case 3:
                    self.accept_ptp_connection()
                case 4:
                    self.enter_chat()
                case 5:
                    self.sign_out()
                    break
                case _:
                    print("Unknown request")

    def sign_up(self):
        self.password = input(
            f"Please enter a {Colours.coloured('password', Colours.OKBLUE)}: ")

        while True:
            self.command(Message.SIGN_UP.value,
                         self.username.encode(), self.password.encode())

            response = self.server.recv(MESSAGE_BYTE_COUNT)
            response_type = response[1]

            if response_type == Message.ACCEPT_SIGN_IN.value:
                print("You've successfully signed up to the server!")
                break

            if response_type == Message.DECLINE_SIGN_IN.value:
                print("Sorry, that username was not accepted by the server")
                self.username = input(
                    f"Please enter a {Colours.coloured('new username', Colours.OKBLUE)}: ")

    def sign_in(self):
        self.password = input(
            f"Please enter your {Colours.coloured('password', Colours.OKBLUE)}: ")

        while True:
            self.command(Message.SIGN_UP.value,
                         self.username.encode(), self.password.encode())

            response = self.server.recv(MESSAGE_BYTE_COUNT)
            response_type = response[1]

            if response_type == Message.ACCEPT_SIGN_IN.value:
                print("You've successfully signed in to the server!")
                break

            if response_type == Message.DECLINE_SIGN_IN.value:
                print(
                    "Sorry, that username and password combination was not accepted by the server")
                self.username = input(
                    f"Please enter your {Colours.coloured('username', Colours.OKBLUE)}: ")
                self.password = input(
                    f"Please enter your {Colours.coloured('username', Colours.OKBLUE)}: ")

    def print_user_list(self, list, empty_text="No visible users"):
        i = 1
        for username in list:
            if username != self.username:
                print(f"({i}) {username}")
                i += 1

        if i == 1:
            print(empty_text)

    def request_user_list(self):
        self.command(Message.REQUEST_USER_LIST.value)

        response = self.server.recv(6)
        list_length = int.from_bytes(response[2:], "little")
        list = self.server.recv(list_length).decode("utf-8").split(", ")

        self.print_user_list(list)

    def request_ptp_connection(self):
        username = input(f"Please enter their {Colours.coloured('username', Colours.OKBLUE)}: ")

        self.command(Message.REQUEST_PTP_CONNECTION.value, username.encode())
        print("Request sent. You will be notified of their response")

    def accept_ptp_connection(self):
        if len(self.ptp_requests) == 0:
            print("No PTP requests")
            return
        
        self.print_user_list(self.ptp_requests)

        username = input(f"Please enter their {Colours.coloured('username', Colours.OKBLUE)}: ")

        if username not in self.ptp_requests:
            print("Unknown username '{username}'")
            return

        chat = Chat()
        chat.run()
        self.chats.append(chat)

        part_1 = ip_address_to_int(chat.ip_address).to_bytes("little")
        info = pad_bytes(part_1 + chat.port.to_bytes("little"), 8)

        self.command(Message.ACCEPT_PTP_CONNECTION.value, username.encode(), info)

        print("Request accepted. You can now view a chat with them")

    def enter_chat(self):
        print("unimplemented")

    def sign_out(self):
        self.command(Message.SIGN_OUT.value,
                     self.username.encode(), self.password.encode())
        self.server.close()
        print("You've been successfully signed out")


class Chat:
    def __init__(self, host, acc_name, req_name):
        self.host = host
        self.acc_name = acc_name
        self.req_name = req_name

    def open_port(self):
        while True:
            random_port = random.randint(15000, 65000)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test_sock:
                if test_sock.connect_ex((self.host, random_port)) == 0:
                    return random_port

    def start(self):
        # Open a TCP socket to communicate intent with the other user
        pass

    def run(self):
        pass


def main():
    print(Colours.coloured("Welcome to Acme Messenger!", Colours.GREEN))

    client = Client(parse_args())
    client.run()


def parse_args():
    # TODO: Fiddle with these a little bit
    parser = argparse.ArgumentParser(
        prog="Acme Messenger",
        description="A peer-to-peer messaging client")

    parser.add_argument("username",
                        help="The username other users will see")

    parser.add_argument("-s", "--signin",
                        action="store_true",
                        help="Whether the client should sign in instead of signing up")

    parser.add_argument("-a", "--ip_address",
                        default="127.0.0.1",
                        help="The IP address of the server (127.0.0.1)")

    parser.add_argument("-p", "--port",
                        default=65432,
                        help="The port number of the server (65432)",
                        type=int)

    parser.add_argument("-i", "--invisible",
                        action="store_true",
                        help="Whether to hide the user's username from other users (False)")

    return parser.parse_args()


if __name__ == "__main__":
    main()
