import numpy as np
import sounddevice as sd
import socket
import signal
import sys
import time
from threading import Thread
from scipy.fft import fft
import queue

# Signal processing global variables
sample_rate = 44100
bit_duration = 0.01
freq_high = 2000
freq_low = 1000
chunk_size = int(bit_duration * 10 * 8)

def generate_sine_wave(frequency, duration=bit_duration, sample_rate=sample_rate):
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

def fsk_demodulate(received_signal, freq_high, freq_low, bit_duration, 
                   sample_rate=sample_rate, threshold_factor=0.55):
    """
    FSK demodulates a received signal.

    Args:
        received_signal (numpy.ndarray): The FSK modulated signal to demodulate.
        freq_high (float): Frequency for the '1' bit in Hz.
        freq_low (float): Frequency for the '0' bit in Hz.
        bit_duration (float): Duration of each bit in seconds.
        sample_rate (int, optional): Number of samples per second. Defaults to 44100.
        threshold_factor (float, optional):  A value between 0 and 1.  Adjusts the
            threshold for determining if a bit is a 0 or 1.  Default is 0.5.

    Returns:
        str: The demodulated bit string.
    """

    demodulated_bits = ""
    num_bits = int(len(received_signal) / (sample_rate * bit_duration))
    
    for i in range(num_bits):
        start_sample = int(i * sample_rate * bit_duration)
        end_sample = int((i + 1) * sample_rate * bit_duration)
        bit_signal = received_signal[start_sample:end_sample]

        # Calculate the energy at each frequency.  More robust than just one sample.
        energy_high = np.sum(np.abs(bit_signal * generate_sine_wave(freq_high)))
        energy_low = np.sum(np.abs(bit_signal * generate_sine_wave(freq_low)))

        # Use a threshold relative to the *sum* of the energies.
        threshold = (energy_high + energy_low) * threshold_factor

        if energy_high > threshold and energy_low < threshold:
            demodulated_bits += '1'
        elif energy_low > threshold and energy_high < threshold:
            demodulated_bits += '0'
    return demodulated_bits

def audio_callback(indata, frames, time, status, audio_queue, freq_high, freq_low, bit_duration, sample_rate):
    """
    Callback function for the sounddevice audio stream.  This function is called
    whenever a new chunk of audio data is available from the microphone.

    Args:
        indata (numpy.ndarray): The audio data from the microphone.
        frames (int): The number of frames in the audio data.
        time (cffi.CData):  Timestamp information (not used here).
        status (int):  Status flags (e.g., for buffer overflows).
        audio_queue (queue.Queue):  A queue to put the audio data into.
        freq_high (float): Frequency for the '1' bit in Hz.
        freq_low (float): Frequency for the '0' bit in Hz.
        bit_duration (float): Duration of each bit in seconds.
        sample_rate (int): Number of samples per second.
    """
    if status:
        print(f"Error in audio stream: {status}")
        return
    # Copy the audio data to the queue.  Use non-blocking to avoid potential issues.
    try:
        audio_queue.put_nowait(indata.copy())
    except queue.Full:
        print("Queue full") 

def stream_audio(sample_rate=sample_rate, chunk_size=chunk_size, 
                 freq_high=freq_high, freq_low=freq_low, 
                 bit_duration=bit_duration):
    """
    Streams audio from the default microphone in a continuous loop.

    Args:
        sample_rate (int, optional): The sampling rate in Hz. Defaults to 44100.
        chunk_size (int, optional): The size of each audio chunk in frames. Defaults to 1024.
        freq_high (float): Frequency for the '1' bit in Hz.
        freq_low (float): Frequency for the '0' bit in Hz.
        bit_duration (float): Duration of each bit in seconds.
    """

    audio_queue = queue.Queue(maxsize=100)  # Create a queue to hold audio data
    try:
        # Open the audio stream.  Importantly, use a non-blocking stream.
        stream = sd.InputStream(samplerate=sample_rate, blocksize=chunk_size,
                                channels=1, callback=(lambda indata, frames, 
                                                      time, status: 
                                                      audio_callback(indata, 
                                                                     frames, time, 
                                                                     status, 
                                                                     audio_queue, 
                                                                     freq_high, 
                                                                     freq_low,
                                                                     bit_duration, 
                                                                     sample_rate)))
        stream.start() # Start the stream.

        print("Audio stream started.  Press Ctrl+C to stop.")
        # Process audio data from the queue in a loop.
        while True:
            try:
                audio_data = audio_queue.get(timeout=1)  # Get data from the queue.
                
                # Demodulate the audio data
                demodulated_bits = fsk_demodulate(audio_data, freq_high, 
                                                  freq_low, bit_duration, 
                                                  sample_rate)
                print(f"Demodulated bits: {demodulated_bits}")

            except queue.Empty:
                pass # No operation
            except KeyboardInterrupt:
                print("Stopping audio stream...")
                stream.stop()
                stream.close()
                break # Exit the loop
    except Exception as e:
        print(f"Error streaming audio: {e}")

if __name__ == "__main__":
    stream_audio(sample_rate, chunk_size, freq_high, freq_low, bit_duration)