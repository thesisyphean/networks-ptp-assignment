import argparse
import socket
import asyncio
from server import Message

# These have been pulled from the Blender build scripts
# Terminal colours are changed by inserting the escape sequence
#  into the string before the text and following it with the
#  end escape sequence


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

    def coloured(message, colour):
        return colour + message + Colors.END


class Client:
    def __init__(self, args):
        self.username = args.username
        self.server_ip_address = args.ip_address
        self.server_port = args.port
    
    def command(self, command_type, param_1=b"\x00" * 8, param_2=b"\x00" * 8):
        self.server.sendall(
            b"\x01" +
            command_type.to_bytes(1, "little") +
            param_1 +
            param_2
        )

    def run(self):
        # Create and bind the server socket
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.connect((self.server_ip_address, self.server_port))
        # This ensures that the socket can be used with coroutines
        # self.server.setblocking(False)

        # The first step is to sign up
        self.sign_up()

        # loop = asyncio.get_event_loop()
        # # Each 
        # while True:
        #     client, _ = await loop.sock_accept(server)
        #     loop.create_task(handle_client(client))
    
    def sign_up(self):
        # TODO: This should actually be the username that gets checked
        while True:
            self.password = input(f"Please enter a {Colors.coloured("password", Colors.OK_BLUE)}: ")

            request = self.command(Message.SIGN_UP, self.username.encode(), self.password.encode())
            self.server.sendall(request)

            response = self.server.recv(18)
            response_type = response[1]

            if 

            if response_type == Message.DECLINE_SIGN_IN.value:
                print("Sorry, th")

    async def handle_client(client):
        loop = asyncio.get_event_loop()
        request = None
        while request != 'quit':
            request = (await loop.sock_recv(client, 255)).decode('utf8')
            response = str(eval(request)) + '\n'
            await loop.sock_sendall(client, response.encode('utf8'))
        client.close()


def main():
    print("Welcome to Acme Messenger!")

    client = Client(parse_args())
    client.run()


def parse_args():
    # TODO: Fiddle with these a little bit
    parser = argparse.ArgumentParser(
        prog="Acme Messenger",
        description="A peer-to-peer messaging client")

    parser.add_argument("username",
                        help="The username other users will see")

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

    return parser.parse_args()


if __name__ == "__main__":
    main()
