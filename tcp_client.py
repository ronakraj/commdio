import socket
import signal
import sys
import time

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 12345        # The port used by the server

def signal_handler(sig, frame):
     print("Exiting the program now.")
     sys.exit(0)

# Catch ctrl+c to exit program at any time
signal.signal(signal.SIGINT, signal_handler)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    while True:
        message = input("Enter message to send (or 'quit' to exit): ")
        if message.lower() == 'quit':
            break
        s.sendall(message.encode())
        #data = s.recv(1024)

        time.sleep(0.01)