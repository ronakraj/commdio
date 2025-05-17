# CommDio - Communications via Audio
This is a simple application that converts messages into audio using
the modulation scheme frequency shift keying (FSK) and transmits the modulation
over the air using your device's speakers. The receiver uses their microphone
to receive the raw audio, before demodulating the FSK and converting bits 
into the original string message. 

This was built as a proof of concept for transferring very small strings of
information between two air gapped devices with audio capability.