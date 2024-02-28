import socket
import threading
import logging

SERVER_IP = '196.24.148.147'
SERVER_PORT_TCP = 5555

active_clients = {}
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)  # Set logging level to INFO


class ClientThread(threading.Thread):
    def __init__(self, tcp_client, addr):
        threading.Thread.__init__(self)
        self.tcp_client = tcp_client
        self.addr = addr

    def run(self):
        try:
            while True:
                data = self.tcp_client.recv(1024).decode('utf-8')
                if not data:
                    logger.info(f"Client {self.addr} disconnected.")
                    break
                message = data.split()
                if message[0] == "REGISTER":
                    self.register_client(message[1], self.tcp_client)
                elif message[0] == "QUERY":
                    self.query_clients(self.tcp_client)
                elif message[0] == "MESSAGE":
                    recipient = message[1]
                    content = ' '.join(message[2:])
                    self.send_message(recipient, content)
        except Exception as e:
            logger.error(f"An error occurred: {e}")
        finally:
            self.tcp_client.close()

    def register_client(self, username, client_socket):
        active_clients[username] = client_socket
        logger.info(f"Registered client: {username}")

    def query_clients(self, client_socket):
        clients = ', '.join(active_clients.keys())
        client_socket.send(f"ACTIVE CLIENTS: {clients}".encode('utf-8'))

    def send_message(self, recipient, content):
        if recipient in active_clients:
            recipient_socket = active_clients[recipient]
            recipient_socket.send(content.encode('utf-8'))
        else:
            logger.warning(f"Client '{recipient}' is not online.")


def main():
    # Set up TCP server
    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server.bind((SERVER_IP, SERVER_PORT_TCP))
    tcp_server.listen(5)
    logger.info(f"TCP server listening on {SERVER_IP}:{SERVER_PORT_TCP}")

    try:
        while True:
            # Accept TCP connections
            tcp_client, addr = tcp_server.accept()
            logger.info(f"Accepted connection from {addr}")
            client_thread = ClientThread(tcp_client, addr)
            client_thread.start()

    except KeyboardInterrupt:
        logger.info("Server shutting down.")
    finally:
        tcp_server.close()


if __name__ == "__main__":
    main()
