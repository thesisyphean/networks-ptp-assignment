import socket
from multiprocessing import Process

class User(Process):
    def __init__(self, conn, addr):
        super().__init__()
        self.conn = conn
        self.addr = addr
    
    def run(self):
        with self.conn:
            self.username = self.conn.recv(50)
            print(f"Connected by {self.addr}, Username: {self.username}")

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
    server = Server()
    server.run()

if __name__ == "__main__":
    main()