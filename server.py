import socket
from multiprocessing import Process
from enum import Enum
import itertools

class Command(Enum):
    ACCEPT_CONNECTION = 0
    SEND_USERNAME = 1
    ACCEPT_USERNAME = 2
    DECLINE_USERNAME = 3
    REQUEST_USER_LIST = 4
    REQUEST_PTP_CONNECTION = 5

class User(Process):
    def __init__(self, conn, addr):
        super().__init__()
        self.conn = conn
        self.addr = addr

        self.username = ""
        self.available = False
        # not visible until specified as such
        self.visible = False
        self.busy = False

    # takes input of command bytes
    # 1 byte for command type, 8 bytes for param 1, 2 bytes for param 2
    # returns command for reply
    def process_command(self, command_bytes):
        command_type = int.from_bytes(command_bytes[:1], 'big')
        # these indices are subject to change based on username length restrictions and encoding
        param_1 = command_bytes[1:9]
        param_2 = command_bytes[9:11]
        
        # print(Command.SEND_USERNAME)
        # bruh wtf why is Command.SEND_USERNAME not evaluating to 1
        # I may be using the enum wrong lmao, but I don't know why
        if command_type == Command.SEND_USERNAME:
            name = param_1.decode('utf-8')
            print(name)
            for user in server.users:
                if user.username == name:
                    # return username taken message
                    return
            self.username = name
            self.available = True
            if int.from_bytes(param_2, 'big') == 1:
                self.visible = True
                
                # send visible users list? May be simpler to just keep that as a separate 
                # command and have the client side automatically request it on connection

            return self.send_command(Command.ACCEPT_USERNAME)

        if command_type == Command.REQUEST_USER_LIST: 
            users = ""
            for user in server.users:
                if user.available and not user.busy:
                    users += user
                    users += ", "
            users = users[:-1]
            # generate data transfer message with user list and return

        if command_type == Command.REQUEST_PTP_CONNECTION:
            pass



        # if statements for each other command the server could recieve

    def process_data_transfer(data_bytes):
        pass
    
    # this is fun lmao
    # pads params 1 and 2 with 0s by default, otherwise assumes values if inputed are padded
    def send_command(self, command_num, param_1=b'\x00'*8, param_2=b'\x00'*2):
        self.conn.sendall(b'\x00' + command_num.to_bytes(1, 'big') + param_1 + param_2)

    def run(self):
        with self.conn:
            print(f"Connected by {self.addr}, Username: {self.username}")
            while True:
                initial_byte = self.conn.recv(1)
                if int.from_bytes(initial_byte, 'big') == 1:
                    # recieve rest of command
                    command_bytes = self.conn.recv(12)
                    self.process_command(command_bytes)
                
                else:
                    # process invalid message (server is never sent a data transfer)
                    pass

class Server:
    # This IP adress is standard for the loopback interface
    # Only processes on the host will be able to connect to the server
    HOST = "127.0.0.1"
    PORT = 65432

    def __init__(self):
        self.users = []

    def run(self):
        print("Server is running!")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.HOST, self.PORT))
            sock.listen()

            while True:
                conn, addr = sock.accept()

                user = User(conn, addr)
                self.users.append(user)
                user.start()

def main():
    global server
    server = Server()
    server.run()

if __name__ == "__main__":
    main()
