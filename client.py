import argparse
import socket

class Client:
    def __init__(self, args):
        self.username = args.username
        self.ip_address = args.ip_address
        self.port = args.port

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.ip_address, self.port))
            print("Connected to the server!")
            sock.sendall(self.username.encode())

def main():
    parser = argparse.ArgumentParser(
        prog="ChatApp",
        description="A ChatApp client")
    
    parser.add_argument("username",
        help="The username other users will see")

    parser.add_argument("-i", "--ip_address",
        default="127.0.0.1",
        help="The IP address of the server (127.0.0.1)")

    parser.add_argument("-p", "--port",
        default=65432,
        help="The port number of the server (65432)",
        type=int)

    args = parser.parse_args()

    client = Client(args)
    client.run()

if __name__ == "__main__":
    main()