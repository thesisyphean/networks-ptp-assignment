import argparse
import socket
from server import Message
import textwrap
import struct
import random
from threading import Thread, Lock
import time
import os

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


# 2 bytes for type of message, and 2 8-byte params
MESSAGE_BYTE_COUNT = 18


def pad_bytes(bytes, length):
    """Pads bytes with null bytes from the left"""
    return bytes + b"\x00" * (length - len(bytes))


def ip_address_to_int(ip_address):
    """Converts an ip address to an integer so it can be sent over a socket"""
    return struct.unpack("!L", socket.inet_aton(ip_address))[0]


def int_to_ip_address(integer):
    """Converts an integer back into an ip address"""
    return socket.inet_ntoa(struct.pack("!L", integer))


class Client:
    """A client for a PTP messaging program that uses UDP sockets to communicate"""
    def __init__(self, args):
        """args must have fields username, ip_address, port, signin"""
        self.username = args.username
        self.server_ip_address = args.ip_address
        self.server_port = args.port
        self.signed_up = args.signin

        self.ptp_requests = []
        self.chats = []

    def command(self, command_type, param_1=b"\x00" * 8, param_2=b"\x00" * 8):
        """Sends the given command to the server, defaulting to null parameters"""
        self.server.sendall(
            # Commands begin with this byte
            b"\x01" +
            command_type.to_bytes(1, "little") +
            # This ensures that the right format is maintained
            pad_bytes(param_1, 8) +
            pad_bytes(param_2, 8)
        )

    def run(self):
        """Connects to the server and repeatedly polls the user"""
        # Create and connect the server socket
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.connect((self.server_ip_address, self.server_port))

        # Get the personal socket that the server will use
        self.server_port = int.from_bytes(self.server.recv(2), "little")
        self.server.close()

        # Reconnect to the new socket
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.connect((self.server_ip_address, self.server_port))

        if self.signed_up:
            self.sign_in()
        else:
            self.sign_up()

        while True:
            print(textwrap.dedent("""
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

            # Get any ptp requests or ptp accepts from the server
            self.check_for_requests()

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

    def check_for_requests(self):
        """Parses any ptp requests or responses"""
        self.server.setblocking(False)

        # If there is no data, recv will throw an error which will be caught and ignored
        try:
            # The only messages we receive from the server at this point
            # are requests, or accepted or declined requests
            response = self.server.recv(MESSAGE_BYTE_COUNT)
            response_type = response[1]

            # We've received a ptp request from the server
            if response_type == Message.RELAY_PTP_REQUEST.value:
                username = response[2:10].decode(
                    "utf-8").rstrip("\0")  # Param 1
                self.ptp_requests.append(username)

            # Another user has accepted our request
            if response_type == Message.ACCEPT_PTP_CONNECTION.value:
                username = response[2:10].decode(
                    "utf-8").rstrip("\0")  # Param 1
                conn_info = response[10:17]  # Param 2

                # Create a new chat with them
                chat = Chat(username)

                # Parse the connection info from param 2
                chat.host = int_to_ip_address(
                    int.from_bytes(conn_info[:4], "little"))
                chat.tcp_port = int.from_bytes(conn_info[4:6], "little")

                self.chats.append(chat)
                Thread(target=chat.start_requester).start()
        except:
            pass

        self.server.setblocking(True)

    def sign_up(self):
        """Creates a new account on the server"""
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

            else:
                print("Sorry, that username was not accepted by the server")
                self.username = input(
                    f"Please enter a {Colours.coloured('new username', Colours.OKBLUE)}: ")

    def sign_in(self):
        """Signs in to a previous account on the server"""
        self.password = input(
            f"Please enter your {Colours.coloured('password', Colours.OKBLUE)}: ")

        while True:
            self.command(Message.SIGN_IN.value,
                         self.username.encode(), self.password.encode())

            response = self.server.recv(MESSAGE_BYTE_COUNT)
            response_type = response[1]

            if response_type == Message.ACCEPT_SIGN_IN.value:
                print("You've successfully signed in to the server!")
                break

            else:
                print(Message(response_type))
                print(
                    "Sorry, that username and password combination was not accepted by the server")
                self.username = input(
                    f"Please enter your {Colours.coloured('username', Colours.OKBLUE)}: ")
                self.password = input(
                    f"Please enter your {Colours.coloured('username', Colours.OKBLUE)}: ")

    def print_user_list(self, list, empty_text="No visible users"):
        """Prints a given list of users"""
        i = 1
        for username in list:
            if username != self.username:
                print(f"({i}) {username}")
                i += 1

        if i == 1:
            print(empty_text)

    def request_user_list(self):
        """Retrieves the current visible users from the server"""
        self.command(Message.REQUEST_USER_LIST.value)

        # This is a data transfer, with the content being the user list
        response = self.server.recv(6)
        list_length = int.from_bytes(response[2:], "little")
        list = self.server.recv(list_length).decode("utf-8").split(", ")

        self.print_user_list(list)

    def request_ptp_connection(self):
        """Sends a PTP connection request to the server"""
        username = input(
            f"Please enter their {Colours.coloured('username', Colours.OKBLUE)}: ")

        self.command(Message.REQUEST_PTP_CONNECTION.value, username.encode())
        print("Request sent. You will be notified of their response")

    def accept_ptp_connection(self):
        """Accepts a PTP connection request via the server, with connection info"""
        if len(self.ptp_requests) == 0:
            print("No PTP requests")
            return

        self.print_user_list(self.ptp_requests)

        username = input(
            f"Please enter their {Colours.coloured('username', Colours.OKBLUE)}: ")

        if username not in self.ptp_requests:
            print(f"Unknown username '{username}'")
            return

        # They can't accept a request again
        self.ptp_requests.remove(username)

        # Create the chat
        chat = Chat(username)
        self.chats.append(chat)
        ip_address, port = chat.get_conn_info()
        Thread(target=chat.start_host).start()

        # Transform the connection info for the requesting client
        part_1 = ip_address_to_int(ip_address).to_bytes(4, "little")
        info = pad_bytes(part_1 + port.to_bytes(2, "little"), 8)

        # and send
        self.command(Message.ACCEPT_PTP_CONNECTION.value,
                     username.encode(), info)

        print("Request accepted. You can now view a chat with them")

    def enter_chat(self):
        """Sets up a chat, clears the screen and prints previous messages"""
        print("Which chat do you want to enter:")

        for i in range(len(self.chats)):
            print(f"({i+1}) {self.chats[i].username}")

        choice = input("Chat number: ")

        if not choice.isdecimal():
            print("Please enter a decimal number")
            return

        choice = int(choice)
        if choice < 1 or choice > len(self.chats):
            print("Please choose an existing chat")
            return

        chat = self.chats[choice - 1]

        # Clear the screen when entering a chat using os-specific commands
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"Chatting with {chat.username}")
        print("Enter a message to send it in real time, or q to quit")

        Thread(target=chat.enter_chat).start()

        # Keep sending messages until q or a keyboard interrupt
        while True:
            try:
                message = input("Your message: ")
            except KeyboardInterrupt:
                chat.leave_chat()
                break

            if message == "q":
                chat.leave_chat()
                break

            chat.send_message(message)

    def sign_out(self):
        """Signs the user out of the server"""
        self.command(Message.SIGN_OUT.value,
                     self.username.encode(), self.password.encode())
        self.server.close()

        for chat in self.chats:
            chat.close()

        print("You've been successfully signed out")


class Chat:
    """Manages a chat between one client and another"""
    def __init__(self, username):
        self.username = username

        self.in_chat = False
        # Previous messages
        self.history = []
        self.udp_lock = Lock()

    def get_conn_info(self):
        """Determines the ip address and generates tcp and udp ports"""
        self.ip_address = socket.gethostbyname(socket.gethostname())
        # Get ports nondeterministically to avoid collisions
        self.tcp_port = random.randint(15000, 65000)
        self.udp_port = random.randint(15000, 65000)

        return self.ip_address, self.tcp_port

    def start_host(self):
        """Sets up the chat for the accepting client"""
        # We use a TCP socket to send data required to set up the UDP socket
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.bind((self.ip_address, self.tcp_port))
        self.tcp_sock.listen()
        self.tcp_sock, _ = self.tcp_sock.accept()

        # Send our UDP port and get their ip address and port
        # (They have our ip address already from the connection info)
        self.tcp_sock.sendall(self.udp_port.to_bytes(4, "little"))
        self.other_udp_port = int.from_bytes(self.tcp_sock.recv(4), "little")
        self.other_ip_address = int_to_ip_address(
            int.from_bytes(self.tcp_sock.recv(4), "little"))

        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.bind((self.ip_address, self.udp_port))

        self.to_address = (self.other_ip_address, self.other_udp_port)

    def start_requester(self):
        """Sets up the chat for the requesting client"""
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # These are set before this method is called
        self.tcp_sock.connect((self.host, self.tcp_port))

        # Get UDP port from other client and send our UDP port
        self.other_udp_port = int.from_bytes(self.tcp_sock.recv(4), "little")
        self.udp_port = random.randint(15000, 65000)
        self.tcp_sock.sendall(self.udp_port.to_bytes(4, "little"))
        self.ip_address = socket.gethostbyname(socket.gethostname())
        self.tcp_sock.sendall(ip_address_to_int(
            self.ip_address).to_bytes(4, "little"))

        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.bind((self.ip_address, self.udp_port))

        self.to_address = (self.host, self.other_udp_port)

    def enter_chat(self):
        """Prints previous messages and polls the server for new ones"""
        # Print the previous messages
        for i in range(len(self.history)):
            message, current_time = self.history[i]
            print(f"Message {i + 1} ({current_time}):\n{message}\n")

        self.in_chat = True

        # Continuously check for sent messages and print them if found
        i = len(self.history)
        while self.in_chat:
            try:
                # This will throw an error if there is no available message, so we catch it
                message, current_time = self.receive_message()
                print(Colours.coloured(
                    f"\nMessage {i + 1} ({current_time}):", Colours.GREEN) + f"\n{message}\n")
                i += 1
            except Exception as e:
                pass

    def leave_chat(self):
        """Stops the polling for messages"""
        self.in_chat = False

    def send_message(self, text):
        """Send a message to the other client"""
        with self.udp_lock:
            encoded_text = text.encode("utf-8")
            length = len(encoded_text).to_bytes(4, "little")
            message = (b"\x00" * 2) + length + encoded_text
            self.udp_sock.sendto(message, self.to_address)

    def receive_message(self):
        """Receive a message from the other client"""
        with self.udp_lock:
            self.udp_sock.setblocking(False)
            buffer, _ = self.udp_sock.recvfrom(1024)
            self.udp_sock.setblocking(True)

            length = int.from_bytes(buffer[2:6], "little")
            content = buffer[6:6 + length].decode("utf-8")
            current_time = time.strftime("%H:%M:%S", time.localtime())

            self.history.append((content, current_time))

            return (content, current_time)

    def close(self):
        """Close all connections"""
        self.tcp_sock.close()
        self.udp_sock.close()


def main():
    print(Colours.coloured("Welcome to messenger!", Colours.GREEN))

    client = Client(parse_args())
    client.run()


def parse_args():
    """Parses all command-line arguments for the program"""
    parser = argparse.ArgumentParser(
        prog="Messenger",
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
