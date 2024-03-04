import argparse
import socket
from server import Message
import textwrap
import struct
import random
from threading import Thread, Lock
import time

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
        self.chats = []

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
            print(textwrap.dedent("""
                  You can:
                  (1) Request the user list
                  (2) Request a PTP connection
                  (3) Accept a PTP connection
                  (4) Enter an active chat
                  (5) Sign out from the server
                  (6) Refresh
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
                case 6:
                    # This is simply to recheck for messages from the server
                    pass
                case _:
                    print("Unknown request")

            self.check_for_requests()
    
    def check_for_requests(self):
        self.server.setblocking(False)

        # If there is no data, recv will throw an error which will be caught and ignored
        try:
            # The only messages we receive from the server at this point
            # are requests, or accepted or declined requests
            response = self.server.recv(MESSAGE_BYTE_COUNT)
            response_type = response[1]

            if response_type == Message.RELAY_PTP_REQUEST.value:
                username = response[2:10].decode("utf-8").rstrip("\0") # Param 1
                self.ptp_requests.append(username)

            if response_type == Message.ACCEPT_PTP_CONNECTION.value:
                username = response[2:10].decode("utf-8").rstrip("\0") # Param 1
                conn_info = response[10:17] # Param 2

                chat = Chat(username)

                chat.host = int_to_ip_address(int.from_bytes(conn_info[:4], "little"))
                chat.tcp_port = int.from_bytes(conn_info[4:6], "little")

                self.chats.append(chat)
                Thread(target=chat.start_requester).start()
        except:
            pass
    
        self.server.setblocking(True)

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

            else:
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

            else:
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
            print(f"Unknown username '{username}'")
            return

        chat = Chat(username)
        self.chats.append(chat)
        ip_address, port = chat.get_conn_info()
        Thread(target=chat.start_host).start()

        part_1 = ip_address_to_int(ip_address).to_bytes(4, "little")
        info = pad_bytes(part_1 + port.to_bytes(2, "little"), 8)

        self.command(Message.ACCEPT_PTP_CONNECTION.value, username.encode(), info)

        print("Request accepted. You can now view a chat with them")

    def enter_chat(self):
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

        print(f"Entering the chat with {chat.username}")
        print("Enter a message to send it in real time, or q to quit")

        Thread(target=chat.enter_chat).start()

        while True:
            message = input("Message: ")

            if message == "q":
                chat.leave_chat()
                break

            chat.send_message(message)

    def sign_out(self):
        self.command(Message.SIGN_OUT.value,
                     self.username.encode(), self.password.encode())
        self.server.close()
        print("You've been successfully signed out")


class Chat:
    def __init__(self, username):
        self.username = username

        self.in_chat = False
        self.history = []
        self.udp_lock = Lock()

    def open_port(self):
        while True:
            # TODO
            random_port = random.randint(15000, 65000)
            #with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test_sock:
            #    if test_sock.connect_ex((socket.gethostname(), random_port)) == 0:
            #        return random_port
            return random_port

    def get_conn_info(self):
        self.ip_address = socket.gethostbyname(socket.gethostname())
        self.tcp_port = self.open_port()
        self.udp_port = self.open_port()

        return self.ip_address, self.tcp_port

    def start_host(self):
        # We use a TCP socket to send data required to set up the UDP socket
        # We also use the tcp_sock to send files because it preserves order and is reliable
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.bind((self.ip_address, self.tcp_port))
        self.tcp_sock.listen()
        self.tcp_sock, _ = self.tcp_sock.accept()

        self.tcp_sock.sendall(self.udp_port.to_bytes(4, "little"))
        self.other_udp_port = int.from_bytes(self.tcp_sock.recv(4), "little")
        self.other_ip_address = int_to_ip_address(int.from_bytes(self.tcp_sock.recv(4), "little"))

        # We use the udp_sock to send text messages because order is less vitally important
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.bind((self.ip_address, self.udp_port))

        self.to_address = (self.other_ip_address, self.other_udp_port)

        print("Successfully connected from the accepter's side!")
        self.send_message("please wowsers")

    def start_requester(self):
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # These are set before this method is called
        self.tcp_sock.connect((self.host, self.tcp_port))

        # Get UDP port from other client and send our UDP port
        self.other_udp_port = int.from_bytes(self.tcp_sock.recv(4), "little")
        self.udp_port = self.open_port()
        self.tcp_sock.sendall(self.udp_port.to_bytes(4, "little"))
        self.ip_address = socket.gethostbyname(socket.gethostname())
        self.tcp_sock.sendall(ip_address_to_int(self.ip_address).to_bytes(4, "little"))

        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.bind((self.ip_address, self.udp_port))

        self.to_address = (self.host, self.other_udp_port)

        print("Successfully connected from the requester's side!")
        time.sleep(1)
        print(self.receive_message())

    def enter_chat(self):
        # TODO: Clear screen
        for i in range(len(self.history)):
            print(f"Message {i + 1}:\n{self.history[i]}\n")

        self.in_chat = True

        i = len(self.history)
        while self.in_chat:
            try:
                # This will throw an error if there is no available message

                message = self.receive_message()
                print(f"Message {i + 1}:\n{message}\n")
            except Exception as e:
                pass

            # TODO: Move this over
            i += 1
    
    def leave_chat(self):
        self.in_chat = False

    def send_message(self, text):
        with self.udp_lock:
            length = len(text).to_bytes(4, "little")
            message = (b"\x00" * 2) + length + text.encode("utf-8")
            self.udp_sock.sendto(message, self.to_address)

    def receive_message(self):
        with self.udp_lock:
            self.udp_sock.setblocking(False)

            buffer, _ = self.udp_sock.recvfrom(1024)
            length = int.from_bytes(buffer[2:6], "little")
            content = buffer[6:6 + length].decode("utf-8")
            self.udp_sock.setblocking(True)

            self.history.append(content)

            return content

    # TODO
    def send_file(self):
        pass

    def receive_file(self):
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
