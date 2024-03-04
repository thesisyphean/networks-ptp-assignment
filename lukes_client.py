import argparse
import socket
from enum import Enum
import logging
import struct
import random
from server import Message
from threading import Thread
import threading
import time

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def pad_bytes(bytes, length):
    return bytes + b"\x00" * (length - len(bytes))


def ip_address_to_int(ip_address):
    return struct.unpack("!L", socket.inet_aton(ip_address))[0]


def int_to_ip_address(integer):
    return socket.inet_ntoa(struct.pack("!L", integer))


class Connection:
    def __init__(self, sock, client, username, address):
        self.sock = sock
        self.client = client
        self.username = username
        self.send_address = address
        self.sock_lock = threading.Lock()
        self.active = True

    def run(self):
        log.debug(f"New thread connected to {self.username}")

        time.sleep(1)
        while self.active:
            self.recieve_message()

    def send_message(self, message):
        encoded = message.encode("utf=8")
        self.sock.sendto(
            b"\x00" + b"\x00" + len(encoded).to_bytes(4, "little") + encoded,
            self.send_address,
        )

    def send_file(self, recipient, filename):
        pass

    # Calls recieve method, decodes, and prints to terminal
    def recieve_message(self):
        msg, addr = self.sock.recvfrom(2048)
        length = int.from_bytes(msg[2:6], "little")
        message = msg[6:].decode()
        print(f"Message from {self.username}: {message}")


class Client:
    def __init__(self, sock):
        self.sock = sock
        self.username = ""
        self.username = ""
        self.logged_in = False
        self.ip_address = "127.0.0.1"
        self.connections = []
        self._connections_lock = threading.Lock()

    def run(self):
        self.process_login()

        while True:
            try:
                if self.sock.recv(1, socket.MSG_PEEK) is not None:
                    bit_0 = self.sock.recv(1)[0]
                    if bit_0 == 1:
                        command_bytes = self.sock.recv(17)
                        self.process_command(command_bytes)

                    # User list from server
                    elif bit_0 == 0:
                        header = self.sock.recv(5)
                        length = int.from_bytes(header[1:], "little")
                        print(f"User list: {self.sock.recv(length).decode()}.")
            except:
                pass
            self.control_flow()
            # wait for server response for better user experience
            time.sleep(1)

    # Takes input for username and password, ensuring they are short enough
    def process_login(self):
        choice = input("Would you like to (L)ogin or (R)egister: ").upper()
        if choice == "R":
            while True:
                self.username = input("Please choose a username, max 8 bytes: ")
                self.password = input("Please choose a password, max 8 bytes: ")
                if len(self.username.encode()) > 8 or len(self.password.encode()) > 8:
                    print("Username or password too long")
                else:
                    break

            self.send_command(
                Message.SIGN_UP.value,
                self.username.encode("utf-8"),
                self.password.encode("utf-8"),
            )

        elif choice == "L":
            while True:
                self.username = input("Enter username, max 8 bytes: ")
                self.password = input("Enter password, max 8 bytes: ")
                if len(self.username.encode()) > 8 or len(self.password.encode()) > 8:
                    print("Username or password too long")
                else:
                    break

            self.send_command(
                Message.SIGN_IN.value,
                self.username.encode("utf-8"),
                self.password.encode("utf-8"),
            )
        else:
            print("Could not interperet input.")
            self.process_login(self)

    def control_flow(self):
        print(
            "Choose an action: Request a (C)onnection, (L)ist online users, (M)essage user, (D)isconnect from user, (R)efresh, (S)ign out"
        )
        choice = input().upper()
        if choice == "C":
            username = input("Enter username: ")
            self.send_command(
                Message.REQUEST_PTP_CONNECTION.value, username.encode("utf-8")
            )
            print("Request sent. You will be notified when there is a response.")
        elif choice == "L":
            self.send_command(Message.REQUEST_USER_LIST.value)
        elif choice == "M":
            # check for if there are no connections
            if len(self.connections) == 0:
                print("There are no active connections.")
            username = input("Enter username: ")
            # find and send message to user
            for connection in self.connections:
                if connection.username.rstrip("\0") == username:
                    message = input("Enter message: ")
                    connection.send_message(message)
                    print("Message sent")
                    return
            print("You do not have an active connection with this user.")
        elif choice == "R":
            print("Refreshing...")
        elif choice == "S":
            self.send_command(
                Message.SIGN_OUT.value, self.username.encode(), self.password.encode()
            )
            print("Bye!")
            exit()
        elif choice == "D":
            if len(self.connections) == 0:
                print("There are no active connections.")
                return
            username = input("Enter username: ")
            for connection in self.connections:
                if connection.username.rstrip("\0") == username:
                    connection.active = False
                    connection.sock.close()
                    self.connections.remove(connection)
                    print("Disconnected")

                    return
        else:
            print("Couldn't interpreret input.")

    # takes input of command bytes
    # 1 byte for command type, 8 bytes for param 1, 2 bytes for param 2
    # returns command for reply
    def process_command(self, command_bytes):
        # log.debug(command_bytes)
        command_type = command_bytes[0]
        # these indices are subject to change based on username length restrictions and encoding
        param_1 = command_bytes[1:9]
        param_2 = command_bytes[9:18]

        if command_type == Message.ACCEPT_SIGN_IN.value:
            print(f"Logged in as {self.username}.")
            self.username_accepted = True
        elif command_type == Message.DECLINE_SIGN_UP.value:
            print("This username is taken.")
            self.process_login()
        elif command_type == Message.DECLINE_SIGN_IN.value:
            print("Incorrect username or password.")
            self.process_login()

        elif command_type == Message.ALREADY_LOGGED_IN.value:
            print("This user is already logged in.")
            self.process_login()

        elif command_type == Message.RELAY_PTP_REQUEST.value:
            print(
                f"The user {param_1.decode()} has requested a peer to peer connection."
            )
            if (
                input("Would you like to accept this connection? (Y)es/(N)o: ").upper()
                == "Y"
            ):
                ip = ip_address_to_int(self.ip_address)
                port = 10000 + random.randint(0, 10000)
                log.debug(f"Port: {port}, ip: {ip}")

                # create new socket and bind to new port
                new_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                new_sock.bind((self.ip_address, port))

                log.debug(ip.to_bytes(4, "little") + port.to_bytes(2, "little"))
                # notify requesting client
                self.send_command(
                    Message.ACCEPT_PTP_CONNECTION.value,
                    param_1,
                    ip.to_bytes(4, "little") + port.to_bytes(2, "little"),
                )
                # Create a connection instance and pass a reference to
                # the current state.
                connection = Connection(
                    new_sock,
                    self,
                    param_1.decode().rstrip("\0"),
                    (self.ip_address, port + 1),
                )
                # Add connection to client's list and manage in new thread
                with self._connections_lock:
                    self.connections.append(connection)
                Thread(target=connection.run).start()
                print(f"Connection with {param_1.decode()} established")
                return

            else:
                self.send_command(Message.DECLINE_PTP_CONNECTION.value, param_1)
        elif command_type == Message.USER_NOT_AVAILABLE.value:
            print("The user to requested to chat is not available")
        elif command_type == Message.DECLINE_PTP_CONNECTION.value:
            print(
                f"The user {param_1.decode()} has declined a peer to peer connection."
            )

        elif command_type == Message.ACCEPT_PTP_CONNECTION.value:
            username = param_1.decode("utf-8")
            print("The user {username} has accepted your connection request.")
            ip_address = int_to_ip_address(int.from_bytes(param_2[:4], "little"))
            port = int.from_bytes(param_2[4:6], "little")
            # create new socket for ptp connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((ip_address, port + 1))
            try:
                connection = Connection(
                    sock, self, username.rstrip("\0"), (ip_address, port)
                )
                with self._connections_lock:
                    self.connections.append(connection)
                # manage socket on new thread
                Thread(target=connection.run).start()
                print(f"Connection with {username} established")
            except:
                log.debug("Connection failed")

    # pads params 1 and 2 with 0s by default, otherwise assumes values if inputed are padded
    def send_command(self, command_num, param_1=b"\x00" * 8, param_2=b"\x00" * 8):
        self.sock.sendall(
            b"\x01"
            + command_num.to_bytes(1, "little")
            + pad_bytes(param_1, 8)
            + pad_bytes(param_2, 8)
        )

    def get_connection(self, recipient):
        with self._connections_lock:
            for connection in self.connections:
                if connection.username == recipient:
                    return connection

    def connections(self):
        with self._connections_lock:
            return self._connections


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

    args = parser.parse_args()

    port = None
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((args.ip_address, args.port))
        print("Connected to the server!")
        port = int.from_bytes(sock.recv(2), "little")
        print(f"Port: {port}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((args.ip_address, port))
        client = Client(sock)
        client.run()


if __name__ == "__main__":
    main()
