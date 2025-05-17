import numpy as np
import sounddevice as sd
import time
import threading
import queue
import sys

def generate_sine_wave(frequency, duration, sample_rate=44100):
    """
    Generates a sine wave.

    Args:
        frequency (float): Frequency of the sine wave in Hz.
        duration (float): Duration of the sine wave in seconds.
        sample_rate (int, optional): Number of samples per second. Defaults to 44100.

    Returns:
        numpy.ndarray: The generated sine wave as a NumPy array.
    """
    time_vector = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    sine_wave = np.sin(2 * np.pi * frequency * time_vector)
    return sine_wave

def fsk_demodulate(received_signal_queue, freq_high, freq_low, bit_duration, sample_rate=44100, threshold_factor=0.5):
    """
    FSK demodulates a received signal from a queue and converts it to an ASCII string.

    Args:
        received_signal_queue (queue.Queue): Queue containing received signal chunks.
        freq_high (float): Frequency for the '1' bit in Hz.
        freq_low (float): Frequency for the '0' bit in Hz.
        bit_duration (float): Duration of each bit in seconds.
        sample_rate (int, optional): Number of samples per second. Defaults to 44100.
        threshold_factor (float, optional):  A value between 0 and 1.  Adjusts the
            threshold for determining if a bit is a 0 or 1.  Default is 0.5.
    """
    demodulated_bits = ""
    ascii_string = ""
    while True:
        try:
            received_signal = received_signal_queue.get(timeout=1)  # Get signal with timeout
            print(received_signal)
            num_bits = int(len(received_signal) / (sample_rate * bit_duration))
            for i in range(num_bits):
                start_sample = int(i * sample_rate * bit_duration)
                end_sample = int((i + 1) * sample_rate * bit_duration)
                bit_signal = received_signal[start_sample:end_sample]
                # Calculate the energy at each frequency.
                energy_high = np.sum(np.abs(bit_signal * generate_sine_wave(freq_high, bit_duration, sample_rate)))
                energy_low = np.sum(np.abs(bit_signal * generate_sine_wave(freq_low, bit_duration, sample_rate)))
                # Use a threshold relative to the sum of the energies.
                threshold = (energy_high + energy_low) * threshold_factor
                if energy_high > threshold:
                    demodulated_bits += '1'
                else:
                    demodulated_bits += '0'

            # Convert demodulated bits to ASCII characters.  We processComplete bytes (8 bits).
            while len(demodulated_bits) >= 8:
                byte_string = demodulated_bits[:8]
                demodulated_bits = demodulated_bits[8:]
                try:
                    ascii_char = chr(int(byte_string, 2))
                    ascii_string += ascii_char
                    print(f"Received ASCII character: {ascii_char}, Full String: {ascii_string}") # Keep printing
                except ValueError:
                    print(f"Invalid byte: {byte_string}") #error message
                    ascii_string += "?"
                    print(f"Received ASCII character: ?, Full String: {ascii_string}") # Keep printing

        except queue.Empty:
            # Handle empty queue (no data received for a while)
            time.sleep(0.1)
            continue  # Continue to the next iteration of the loop

def receive_audio(received_signal_queue, duration=10, sample_rate=44100):
    """
    Records audio from the computer's microphone and puts it into a queue.

    Args:
        received_signal_queue (queue.Queue): Queue to put received signal chunks into.
        duration (float): Duration of each recording chunk in seconds. Defaults to 10.
        sample_rate (int, optional): Number of samples per second. Defaults to 44100.
    """
    print("Starting continuous recording...")
    while True:
        recorded_signal = sd.rec(int(duration * sample_rate), 
                                 samplerate=sample_rate, channels=1)
        sd.wait()
        recorded_signal = recorded_signal.flatten()
        received_signal_queue.put(recorded_signal)

def receive_thread(received_signal_queue, sample_rate):
    """
    Thread function to receive audio continuously.
    """
    receive_audio(received_signal_queue, sample_rate)

if __name__ == "__main__":
    # Parameters
    freq_high = 2000  # Frequency for '1' (Hz)
    freq_low = 1000  # Frequency for '0' bit (Hz)
    bit_duration = 0.1  # Duration of each bit (seconds)
    sample_rate = 44100  # Samples per second
    threshold_factor = 0.3  # Adjust this threshold as needed.
    chunk_duration = 0.1  # Duration of each received audio chunk in seconds

    # 1. Reception (Continuous with threads and queue)
    received_signal_queue = queue.Queue()  # Create a queue for received signals

    # Create threads for receiving
    receive_thread_obj = threading.Thread(target=receive_thread, 
                                          args=(received_signal_queue, 
                                                sample_rate))
    receive_thread_obj.start()

    # 2. Demodulation (happens in a separate thread)
    demodulate_thread_obj = threading.Thread(target=fsk_demodulate, 
                                             args=(received_signal_queue, 
                                                   freq_high, freq_low, 
                                                   bit_duration, sample_rate, 
                                                   threshold_factor))
    demodulate_thread_obj.start()

    # Keep the main thread alive to allow the other threads to run.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping threads...")
        demodulate_thread_obj.stop()
        receive_thread_obj.stop()
        sys.exit(0)
        # Add code here to stop the threads more gracefully if needed.
        pass