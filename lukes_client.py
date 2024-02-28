import argparse
import socket

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
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.server_ip_address, self.server_port))
            print("Connected to the server!")

            self.sock = sock
            command_val = 1
            sock.sendall(b'\x01' + b'\x01' + "aaaaaaaa".encode('utf-8') + b'\x00'*2)
            # self.set_usernme()

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
