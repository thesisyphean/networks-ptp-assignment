import socket

HOST = "127.0.0.1"
PORT = 65432

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # This IP adress is standard for the loopback interface
        # Only processes on the host will be able to connect to the server
        sock.bind((HOST, PORT))

        sock.listen()

        while True:
            conn, addr = sock.accept()

            with conn:
                username = conn.recv(2048)
                print(f"Connected by {addr}, Username: {username}")

if __name__ == "__main__":
    main()