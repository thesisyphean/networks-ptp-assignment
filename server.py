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

# converts int to array of bits
def bitfield(n):
    return [1 if digit=='1' else 0 for digit in bin(n)[2:]]

# converts array of bits to int
# DOESNT WORK
def bitfield_to_int(bitfield):
    result = 0

    for i in range(0, len(bitfield), -1):
        result &= 1 << ()
        
    return result

# converts with ascii vals
# assumes bitfield length is a multiple of 8
def bitfield_to_str(bitfield):
    str = ""
    try: 
        for i in range(0, len(bitfield), 8):
            str += chr(bitfield_to_int(bitfield[i:i + 8]))
    except:
        print("Invalid Username")
        return
    return str


def complete_bitfield(bytes):
    return list(itertools.chain_from_i)

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

    # assumes input is bitfield starting at first command bit
    # 1 byte for command type, 8 bytes for param 1, 2 bytes for param 2
    # returns command for reply
    def process_command(self, command_bits):
        command_type = bitfield_to_int(command_bits[:8])
        # these indices are subject to change based on username length restrictions and encoding
        param_1 = command_bits[8:72]
        param_2 = command_bits[72:88]

        if command_type == Command.SEND_USERNAME:
            name = bitfield_to_str(param_1)
            if name is None:
                # return decline username command
                pass
            else:
                self.username = name
                self.available = True
                # add to available users
                if bitfield_to_int(param_2) == 1:
                    self.visible = True
                
                # send visible list 
                # return accept username command

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

    def generate_command(command_name, param_1, param_2)

    def run(self):
        with self.conn:
            print(f"Connected by {self.addr}, Username: {self.username}")
            while True:
                initial_byte = self.conn.recv(1)
                if int.from_bytes(initial_byte) == 1:
                    # recieve rest of command
                    command_bytes = self.conn.recv(12)
                    # not complete
                    self.proccess_command(bitfield(int.from_bytes(command_bytes)))
            

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
    # bitfield = [0, 0, 1, 0, 1, 0, 0, 1]
    # print(bitfield_to_int(bitfield))
    # print(bitfield_to_str(bitfield))

if __name__ == "__main__":
    main()
