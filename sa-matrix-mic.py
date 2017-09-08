import sys
import pyaudio
from struct import unpack
import numpy as np
from dotstar import Adafruit_DotStar

NUMPIXELS = 900

strip = Adafruit_DotStar(NUMPIXELS, 1000000)

strip.begin()
strip.show()

#setup grid mapping for matrix display
sizeX = 30
sizeY = 15

pixelGrid = [[0 for x in range(sizeX)] for y in range(sizeY)]

keyVal = 840
for j in range(sizeY):

    for i in range(sizeX):
	if(j % 2 == 0):
        	rawVal = keyVal + (i*2)
	else:
		rawVal = keyVal - (i*2)
        pixelGrid[j][i] = rawVal

    if(j % 2 == 0):
        keyVal = keyVal - 2
    else:
        keyVal = keyVal - 118

#frequency response scaling
senseVal = 8
bassAdj = 2*senseVal
midAdj = 1*senseVal
trebleAdj = 2*senseVal

spectrum  = [1,1,1,3,3,3,2,2]
matrix    = [0,0,0,0,0,0,0,0]
power     = []
weighting = [4,8,16,32,64,128,256,512] 

def list_devices():
    # List all audio input devices
    p = pyaudio.PyAudio()
    i = 0
    n = p.get_device_count()
    while i < n:
        dev = p.get_device_info_by_index(i)
        if dev['maxInputChannels'] > 0:
           print(str(i)+'. '+dev['name'])
        i += 1

# Audio setup
no_channels = 1
sample_rate = 44100

# Chunk must be a multiple of 8
# NOTE: If chunk size is too small the program will crash
# with error message: [Errno Input overflowed]
chunk = 8192 

list_devices()
# Use results from list_devices() to determine your microphone index
device = 2 

p = pyaudio.PyAudio()
stream = p.open(format = pyaudio.paInt16,
                channels = no_channels,
                rate = sample_rate,
                input = True,
                frames_per_buffer = chunk,
                input_device_index = device)


# Return power array index corresponding to a particular frequency
def piff(val):
    return int(2*chunk*val/sample_rate)
   
def calculate_levels(data, chunk,sample_rate):
    global matrix
    # Convert raw data (ASCII string) to numpy array
    data = unpack("%dh"%(len(data)/2),data)
    data = np.array(data, dtype='h')
    # Apply FFT - real data
    fourier=np.fft.rfft(data)
    # Remove last element in array to make it the same size as chunk
    fourier=np.delete(fourier,len(fourier)-1)
    # Find average 'amplitude' for specific frequency ranges in Hz
    power = np.abs(fourier)   
    matrix[0]= int(np.mean(power[piff(0)    :piff(156):1]))*bassAdj
    matrix[1]= int(np.mean(power[piff(156)  :piff(313):1]))*bassAdj
    matrix[2]= int(np.mean(power[piff(313)  :piff(625):1]))*midAdj
    matrix[3]= int(np.mean(power[piff(625)  :piff(1250):1]))*midAdj
    matrix[4]= int(np.mean(power[piff(1250) :piff(2500):1]))*midAdj
    matrix[5]= int(np.mean(power[piff(2500) :piff(5000):1]))*midAdj
    matrix[6]= int(np.mean(power[piff(5000) :piff(10000):1]))*trebleAdj
    matrix[7]= int(np.mean(power[piff(10000):piff(20000):1]))*trebleAdj
    # Tidy up column values for the LED matrix
    matrix=np.divide(np.multiply(matrix,weighting),1000000)
    # Set floor at 0 and ceiling at 8 for LED matrix
    matrix=matrix.clip(0,8)
    return matrix

# Main loop
while 1:
    try:
        # Get microphone data
        data = stream.read(chunk)
        matrix=calculate_levels(data, chunk,sample_rate)
        strip.clear()
        for y in range (0,8):
            for x in range(0, matrix[y]):
                strip.setPixelColor(pixelGrid[x][y], 255,255,255)
        strip.show()
    except KeyboardInterrupt:
        print("Ctrl-C Terminating...")
        stream.stop_stream()
        stream.close()
        p.terminate()
        sys.exit(1)
    except Exception, e:
        print(e)
        print("ERROR Terminating...")
        stream.stop_stream()
        stream.close()
        p.terminate()
        sys.exit(1)
