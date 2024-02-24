import socket

HOST = "127.0.0.1"
PORT = 65432

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # This IP adress is standard for the loopback interface
        # Only processes on the host will be able to connect to the server
        sock.bind((HOST, PORT))

        sock.listen()

        for _ in range(3):
            conn, addr = sock.accept()

            with conn:
                print(f"Connected by {addr}")

                while True:
                    data = conn.recv(2048)

                    # When the data is an empty bytes object, the connection was closed
                    if not data:
                        break

                    conn.sendall(data + " KaraboTorturing4Life".encode())

if __name__ == "__main__":
    main()