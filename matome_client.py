import argparse
import socket
import textwrap
import struct
import random
from server import Message

MESSAGE_BYTE_COUNT = 18

class ChatClient:
  def __init__(self):
    self.userName = ""
    self.serverIpAddress = ""
    self.serverPort = 0
    self.signedUp = False
    self.ptpRequests = []
    self.chats = []

  def sendCommand(self, commandType, param1=b"\x00" * 8, param2=b"\x00" * 8):
    self.server.sendall(
      b"\x01" +
      commandType.to_bytes(1, "little") +
      self.padBytes(param1, 8) +
      self.padBytes(param2, 8)
    )

  def run(self, args):
    self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.server.connect((args.server_ip_address, args.server_port))
    self.serverPort = int.from_bytes(self.server.recv(2), "little")
    self.server.close()
    self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.server.connect((args.server_ip_address, self.serverPort))

    if args.sign_in:
      self.signIn()
    else:
      self.signUp()

    while True:
      print(textwrap.dedent("""\
         You can:
         (1) Request the user list
         (2) Request a PTP connection
         (3) Accept a PTP connection
         (4) Enter an active chat
         (5) Sign out from the server
         Please enter your choice as a number:"""))

      choice = input()
      if not choice.isdecimal():
        continue

      choice = int(choice)
      if choice == 1:
        self.requestUserList()
      elif choice == 2:
        self.requestPtpConnection()
      elif choice == 3:
        self.acceptPtpConnection()
      elif choice == 4:
        self.enterChat()
      elif choice == 5:
        self.signOut()
        break
      else:
        print("Unknown request")

  def signUp(self):
    self.userName = input("Please enter your username: ")
    self.password = input("Please enter a password: ")

    while True:
      self.sendCommand(Message.SIGN_UP.value,
             self.userName.encode(), self.password.encode())

      response = self.server.recv(MESSAGE_BYTE_COUNT)
      responseType = response[1]

      if responseType == Message.ACCEPT_SIGN_IN.value:
        print("You've successfully signed up to the server!")
        break

      if responseType == Message.DECLINE_SIGN_IN.value:
        print("Sorry, that username was not accepted by the server")
        self.userName = input(
          "Please enter a new username: ")

  def signIn(self):
    self.userName = input("Please enter your username: ")
    self.password = input("Please enter your password: ")

    while True:
      self.sendCommand(Message.SIGN_UP.value,
             self.userName.encode(), self.password.encode())

      response = self.server.recv(MESSAGE_BYTE_COUNT)
      responseType = response[1]

      if responseType == Message.ACCEPT_SIGN_IN.value:
        print("You've successfully signed in to the server!")
        break

      if responseType == Message.DECLINE_SIGN_IN.value:
        print(
          "Sorry, that username and password combination was not accepted by the server")
        self.userName = input(
          "Please enter your username: ")
        self.password = input(
          "Please enter your password: ")

  def printUserList(self, userList, emptyText="No visible users"):
    i = 1
    for username in userList:
      if username != self.userName:
        print(f"({i}) {username}")
        i += 1

    if i == 1:
      print(emptyText)

  def requestUserList(self):
    self.sendCommand(Message.REQUEST_USER_LIST.value)

    response = self.server.recv(6)
    listLength = int.from_bytes(response[2:], "little")
    userList = self.server.recv(listLength).decode("utf-8").split(", ")

    self.printUserList(userList)

  def requestPtpConnection(self):
    userName = input("Please enter the username of the user you want to connect to: ")

    self.ptpRequests.append(userName)
    self.sendCommand(Message.REQUEST_PTP_CONNECTION.value, userName.encode())
    print("Request sent. You will be notified of their response")

  def acceptPtpConnection(self):
    if len(self.ptpRequests) == 0:
      print("No PTP requests")
      return
     
    self.printUserList(self.ptpRequests)

    userName = input("Please enter the username of the user you want to accept the connection from: ")

    if userName not in self.ptpRequests:
      print(f"Unknown username '{userName}'")
      return

    self.sendCommand(Message.ACCEPT_PTP_CONNECTION.value, userName.encode())

    # Go straight to enter chat
    self.enterChat(userName)

  def enterChat(self, chosenUser=None):
    if not chosenUser:
      userList = self.requestUserList()
      if not userList:
        print("No users available to chat with.")
        return

      print("Select a user to enter chat:")
      self.printUserList(userList)
      choice = input("Enter the number of the user: ")

      if not choice.isdigit() or int(choice) < 1 or int(choice) > len(userList):
        print("Invalid choice.")
        return

      chosenUser = userList[int(choice) - 1]

    # Initiating chat with the chosen user
    self.initiateChat(chosenUser)

  def initiateChat(self, chosenUser):
    print(f"Initiating chat with {chosenUser}...")

    # For simplicity, let's assume you just print messages back and forth
    print("Chat started. Type 'exit' to end the chat.")
    while True:
      message = input(f"You: ")
      if message.lower() == "exit":
        print("Chat ended.")
        break
      else:
        print(f"{chosenUser}: {message}")

  def signOut(self):
    self.sendCommand(Message.SIGN_OUT.value)
    print("You have signed out from the server.")

  def padBytes(self, bytes, length):
    return bytes + b"\x00" * (length - len(bytes))

  def ipAddressToInt(self, ipAddress):
    return struct.unpack("!L", socket.inet_aton(ipAddress))[0]

class Chat:
  def __init__(self, host, accName, reqName):
    self.host = host
    self.accName = accName
    self.reqName = reqName

  def openPort(self):
    while True:
      randomPort = random.randint(15000, 65000)
      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as testSock:
        if testSock.connect_ex((self.host, randomPort)) == 0:
          return randomPort

  def start(self):
    pass

  def run(self):
    pass

def main():
  print("Welcome to Chat CPT!")

  client = ChatClient()
  args = argparse.Namespace(
    sign_in=input("Would you like to sign in? (y/n): ").lower() == "y",
    server_ip_address=input("Please enter the IP address of the server (default is 196.47.221.198): ") or "196.47.221.198",
    server_port=int(input("Please enter the port number of the server (default is 65432): ") or 65432)
  )
  client.run(args)

if __name__ == "__main__":
  main()
    
