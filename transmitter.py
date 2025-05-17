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

# Signal processing global variables
sample_rate = 44100
bit_duration = 0.01
freq_high = 2000
freq_low = 1000

def signal_handler(sig, frame):
     print("Exiting the program now.")
     sys.exit(0)

# Catch ctrl+c to exit program at any time
signal.signal(signal.SIGINT, signal_handler)

def generate_sine_wave(frequency, duration=bit_duration, 
                       sample_rate=sample_rate):
    """
    Generates a sine wave.

    Args:
        frequency (float): Frequency of the sine wave in Hz.
        duration (float): Duration of the sine wave in seconds.
        sample_rate (int, optional): Number of samples per second. Defaults to 44100.

    Returns:
        numpy.ndarray: The generated sine wave as a NumPy array.
    """
    time_vector = np.linspace(0, duration, int(sample_rate * duration), 
                              endpoint=False)
    sine_wave = np.sin(2 * np.pi * frequency * time_vector)
    return sine_wave

def generate_fsk_signal(data, freq_high=freq_high, freq_low=freq_low, 
                        sample_rate=sample_rate, 
                        duration=bit_duration) -> np.array:
    """
    Generates an FSK signal for a given binary string.
    """
    samples_per_bit = int(sample_rate * duration)
    time_vector = np.linspace(0, duration, samples_per_bit, endpoint=False)
    signal = np.array([])
    for bit in data:
        if bit == '1':
            signal = np.concatenate([signal, 
                                     generate_sine_wave(freq_high, duration)])
        else:
            signal = np.concatenate([signal, 
                                     generate_sine_wave(freq_low, duration)])
    return signal

def play_audio(signal, sample_rate=sample_rate):
    """
    Plays the given audio signal.
    """
    sd.play(signal, sample_rate)
    sd.wait()

def receive(client_socket, addr):
    global clients

    while True:
        try:
            data = client_socket.recv(1024).decode("utf-8")
            if data == "quit":
                print("Connection interrupted.")
                client_socket.close()
                break
            elif data != "":
                print(f"Received from {addr}: {data}")

                # Transmit received message over air as FSK modulated audio
                # Convert ascii string to binary first
                data_binary = bin(int.from_bytes(data.encode(), 'big'))
                fsk_signal = generate_fsk_signal(data_binary)
                print(f"Sending over air: {data}")
                play_audio(fsk_signal)
            else:
                print("Connection interrupted.")
                client_socket.close()
                break

        except Exception as ex:
            print(f"Exception: {ex}")
            print("Connection interrupted.")
            client_socket.close()
            break

        time.sleep(0.01)
    
    client_socket.close()
    if client_socket in clients:
        clients.remove(client_socket)

def main():
    """
    Main loop for receiving messages over TCP socket, modulating and 
    transmitting.
    """

    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Create a server
    server_socket.bind((host, port))
    server_socket.listen()

    print(f"Server listening on {host}:{port}")

    while True:
        # Make connections to clients
        client_socket, addr = server_socket.accept()
        print(f"Connection established: {addr[0]}:{addr[1]}")
        clients.append(client_socket)
        Thread(target=receive, args=(client_socket, addr)).start()

        time.sleep(0.01)

if __name__ == "__main__":
    main()