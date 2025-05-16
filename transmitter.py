import numpy as np
import sounddevice as sd
import socket
import signal
import sys
import time
from threading import Thread

# Define the host and port
host = "127.0.0.1"
port = 12345
clients = []

def generate_fsk_signal(data, freq1=1000, freq2=2000, sample_rate=44100, 
                        duration=0.1):
    """
    Generates an FSK signal for given binary data.
    """

    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    signal = np.array([])
    for bit in data:
        if bit == '1':
            signal = np.concatenate([signal, np.sin(2 * np.pi * freq1 * t)])
        else:
            signal = np.concatenate([signal, np.sin(2 * np.pi * freq2 * t)])
    return signal

def play_audio(signal, sample_rate=44100):
    """
    lays the given audio signal.
    """
    sd.play(signal, sample_rate)
    sd.wait()

def signal_handler(sig, frame):
     print("Exiting the program now.")
     sys.exit(0)

# Catch ctrl+c to exit program at any time
signal.signal(signal.SIGINT, signal_handler)

def receive(client, addr):
    global clients

    while True:
        try:
            data = client.recv(1024).decode("utf-8")
            if data == "quit":
                print("Connection interrupted.")
                break
            else:
                print(f"Received from {addr}: {data}")

                # Transmit received message over air as FSK modulated audio
                # Convert ascii string to binary first
                data_binary = bin(int.from_bytes(data.encode(), 'big'))
                fsk_signal = generate_fsk_signal(data_binary)
                play_audio(fsk_signal)
                print(f"Sent over air: {data}")

        except Exception as ex:
            print(f"Exception: {ex}")
            print("Connection interrupted.")
            break

        time.sleep(0.01)
    
    if client in clients:
        clients.remove(client)

def main():
    # Create a socket object
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Create a server
    s.bind((host, port))
    s.listen()
    print(f"Server listening on {host}:{port}")

    while True:
        # Make connections to clients
        client, addr = s.accept()
        print(f"Connection established: {addr[0]}:{addr[1]}")
        clients.append(client)
        Thread(target=receive, args=(client, addr)).start()

        time.sleep(0.01)

if __name__ == "__main__":
        main()