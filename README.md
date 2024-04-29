# Networks Peer-to-Peer Assignment

## Overview

This project explores TCP and UDP socket programming and involves creating a chat application through which users can chat over a peer-to-peer connection. The clients connect to the server via TCP and can query it about other present and visible clients. Clients can then request a connection with any of these other clients and, if accepted, open a UDP connection through which to send messages. The content of chats are saved as users move between them and messages include timestamps. Report.pdf contains a more comprehensive description of the project.

## Usage

The server can be started with `python server.py` and runs on the loopback interface on port 65432.
The client can be started with `python client.py <username>` where username is required. The client also takes other command-line arguments, such as the IP address and port of the server, as listed by `python client.py -h`.

## Messages

Report.pdf contains the format and a full description of the messages used by the client and server to communicate.
