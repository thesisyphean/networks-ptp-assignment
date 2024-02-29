import argparse
import socket
from enum import Enum

# TODO: Cut these down
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class Command(Enum):
    ACCEPT_CONNECTION = 0
    SEND_USERNAME = 1
    ACCEPT_USERNAME = 2
    DECLINE_USERNAME = 3
    REQUEST_USER_LIST = 4
    REQUEST_PTP_CONNECTION = 5


def colour(message, colour):
    return colour + message + Colors.END

# MAIN_MESSAGE = f"{colour("Welcome to ChatApp!", Colors.GREEN)}\n(1) List all users."

class Client:
    def __init__(self, args):
        # self.username = args.username
        self.server_ip_address = args.ip_address
        self.server_port = args.port
    
    # def set_username(self):
    #     while True:
    #         # username = 
    #         self.sock.sendall(...) # TODO: Protocol for setting 

    def run(self):
        port = None
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.server_ip_address, self.server_port))
            print("Connected to the server!")
            port = int.from_bytes(sock.recv(2), 'little')
            print(f"Port: {port}")
       

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.server_ip_address, port))
            # self.sock = sock
            command_val = 1
            sock.sendall(b'\x01' + b'\x01' + "aaaaaaaa".encode('utf-8') + b'\x00'*2)
            
            # self.set_usernme()

            while True:
                command_bytes = sock.recv(12)
                self.process_command(command_bytes)

     # takes input of command bytes
    # 1 byte for command type, 8 bytes for param 1, 2 bytes for param 2
    # returns command for reply
    def process_command(self, command_bytes):
        command_type = int.from_bytes(command_bytes[:1], 'big')
        # these indices are subject to change based on username length restrictions and encoding
        param_1 = command_bytes[1:9]
        param_2 = command_bytes[9:11]
        print(command_type)
        if command_type == Command.ACCEPT_USERNAME.value:
            print("hey hey hey")


def main():
    parser = argparse.ArgumentParser(
        prog="ChatApp",
        description="A ChatApp client")
    
    # parser.add_argument("username",
    #     help="The username other users will see")

    parser.add_argument("-i", "--ip_address",
        default="127.0.0.1",
        help="The IP address of the server (127.0.0.1)")

    parser.add_argument("-p", "--port",
        default=65432,
        help="The port number of the server (65432)",
        type=int)
    
    parser.add_argument("-s", "--invisible",
        action="store_true",
        help="Whether to hide the user's username from other users (False)")

    args = parser.parse_args()

    client = Client(args)
    client.run()

if __name__ == "__main__":
    main()
