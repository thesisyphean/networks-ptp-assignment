import socket

SERVER_IP = '196.47.216.30'
SERVER_PORT_TCP = 5555

def main():
    # Set up TCP client
    tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        tcp_client.connect((SERVER_IP, SERVER_PORT_TCP))
        print("Connected to server.")
        
        while True:
            command = input("Enter command (REGISTER, QUERY, or MESSAGE): ").strip().upper()

            if command == "REGISTER":
                username = input("Enter username: ").strip()
                if username:
                    tcp_client.send(f"REGISTER {username}".encode('utf-8'))
                else:
                    print("Username cannot be empty.")

            elif command == "QUERY":
                tcp_client.send("QUERY".encode('utf-8'))
                response = tcp_client.recv(1024).decode('utf-8')
                print(response)

            elif command == "MESSAGE":
                recipient = input("Enter recipient: ").strip()
                message = input("Enter message: ").strip()
                if recipient and message:
                    tcp_client.send(f"MESSAGE {recipient} {message}".encode('utf-8'))
                else:
                    print("Recipient and message cannot be empty.")

            else:
                print("Invalid command. Please enter REGISTER, QUERY, or MESSAGE.")

    except ConnectionRefusedError:
        print("Connection refused. Make sure the server is running.")
    except KeyboardInterrupt:
        print("Client closing.")
    finally:
        tcp_client.close()

if __name__ == "__main__":
    main()
