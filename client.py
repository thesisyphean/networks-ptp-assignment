import argparse
import socket

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

    connect(args)

def connect(args):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((args.ip_address, args.port))
        print("Connected to the server!")
        sock.sendall(args.username.encode())

if __name__ == "__main__":
    main()