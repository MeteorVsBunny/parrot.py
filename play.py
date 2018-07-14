import numpy as np
import pyaudio
import wave
import time
import scipy
import scipy.io.wavfile
from scipy.fftpack import fft, rfft, fft2
from sklearn.externals import joblib
import hashlib
import os
from pyautogui import press, hotkey, click, scroll, typewrite, moveRel
from scipy.fftpack import fft, rfft, fft2, dct
from python_speech_features import mfcc
import pyautogui
import winsound
pyautogui.FAILSAFE = False
import random
import operator
import audioop
import math

TEMP_FILE_NAME = "play.wav"
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
CHUNK = 1024
RECORD_SECONDS = 0.1

def hash_directory_to_number( setdir ):
	return float( int(hashlib.sha256( setdir.encode('utf-8')).hexdigest(), 16) % 10**8 )

def getWavSegment( stream, frames ):	
	range_length = int(RATE / CHUNK * RECORD_SECONDS)
	frames = frames[5:]
	frame_length = len( frames )
	
	intensity = []
	for i in range( frame_length, range_length):
		data = stream.read(CHUNK)
		peak = audioop.maxpp( data, 4 ) / 32767
		intensity.append( peak )
		frames.append(data)

	highestintensity = np.amax( intensity )
	return frames, highestintensity


# Generate the label mapping
labelDict = {}
dir_path = os.path.join( os.path.dirname(os.path.realpath(__file__)), "dataset")
data_directory_names = os.listdir( dir_path )
seperator = ", "
print( "Predicting sounds using machine learning with the following categories: " )
print( seperator.join(data_directory_names) )
for directoryname in data_directory_names:
	labelDict[ str( hash_directory_to_number( os.path.join( dir_path, directoryname ) ) ) ] = directoryname

# Load the trained classifier
classifier = joblib.load( "train.pkl" )	

# Start streaming microphone data
label_array = classifier.classes_
print ( "Listening..." )
frames = []

def throttled_press_detection( currentDict, previousDict, label ):
	currentProbability = currentDict[ label ]
	previousProbability = previousDict[ label ]
	
	if( currentProbability > 70 and previousProbability < 70 ):
		return True
	elif( previousProbability < 70 and ( previousProbability + currentProbability ) / 2 > 50 ):
		return True
	else:
		return False

def continuous_detection( currentDict, previousDict, label ):
	currentProbability = currentDict[ label ]
	previousProbability = previousDict[ label ]
	
	if( currentProbability > 80 ):
		return True
	else:
		return False

def loud_detection( data, label ):
	percent_met = data[-1][label]['percent'] >= 80
	
	if( percent_met ):
		return True
	else:
		return False

def medium_detection( data, label, required_percent, required_intensity ):
	last_is_not_label = data[-1][label]['percent'] < required_percent
	is_previous_label = data[-2][label]['percent'] >= required_percent and data[-2][label]['intensity'] >= required_intensity
	
	# Detect first signs of a medium length sound
	if( is_previous_label and last_is_not_label ):
		avg_percent = ( data[-2][label]['percent'] + data[-3][label]['percent'] + data[-4][label]['percent'] + data[-5][label]['percent'] + data[-6][label]['percent'] ) * 0.2
		avg_intensity = ( data[-2][label]['intensity'] + data[-3][label]['intensity'] + data[-4][label]['intensity'] + data[-5][label]['intensity'] + data[-6][label]['intensity'] ) * 0.2
		
		start_sound_not_label = data[-7][label]['percent'] < required_percent and data[-7][label]['intensity'] < required_intensity
		return avg_intensity >= required_intensity and avg_percent >= required_percent and start_sound_not_label
	return False		
		
def long_detection( data, label, required_percent, required_intensity ):
	last_is_not_label = data[-1][label]['percent'] < required_percent
	is_previous_label = data[-2][label]['percent'] >= required_percent and data[-2][label]['intensity'] >= required_intensity
	
	# Detect first signs of a long length sound
	if( is_previous_label and last_is_not_label ):
		avg_percent = ( data[-2][label]['percent'] + data[-3][label]['percent'] + data[-4][label]['percent'] + data[-5][label]['percent'] 
			+ data[-6][label]['percent'] + data[-7][label]['percent'] + data[-8][label]['percent'] + data[-9][label]['percent'] ) * 0.11
		avg_intensity = ( data[-2][label]['intensity'] + data[-3][label]['intensity'] + data[-4][label]['intensity'] + data[-5][label]['intensity'] 
			+ data[-6][label]['intensity'] + data[-7][label]['intensity'] + data[-8][label]['intensity'] + data[-9][label]['intensity'] ) * 0.11
		
		print( avg_percent, avg_intensity )
		
		return avg_intensity >= required_intensity and avg_percent >= required_percent
	return False
		
def single_tap_detection( data, label, required_percent, required_intensity ):
	percent_met = data[-1][label]['percent'] >= required_percent
	rising_sound = data[-1][label]['intensity'] > data[-2][label]['intensity']
	first_sound = data[-2][label]['percent'] < required_percent
	previous_rising = data[-2][label]['percent'] >= required_percent and data[-2][label]['intensity'] < data[-3][label]['intensity']
	is_winner = data[-1][label]['winner']
	if( is_winner and percent_met and rising_sound and data[-1][label]['intensity'] >= required_intensity ):
		print( "Detecting single tap for " + label )
		return True
	else:
		return False

def quick_detection( currentDict, previousDict, label ):
	currentProbability = currentDict[ label ]
	if( currentProbability > 60 ):
		return True
	else:
		return False

		
def game_label( label ):
	print( label )
	if( label == "cluck" ):
		press('q')
		#click(button='left')
	elif( label == "finger_snap" ):
		click()
	elif( label == "sound_uh" or label == "sound_a" ):
		press('q')
	elif( label == 'sound_s' ):
		press('w')
	elif( label == 'sound_f' ):
		press('e')
	elif( label == "sound_ax" ):
		press('d')
	elif( label == "sound_lol" ):
		press('z')		
	elif( label == "sound_whistle" ):
		press('r')
	elif( label == "sound_oe" ):
		press('1')

def press_label( label ):
	if( label == "cluck" ):
		click()
	elif( label == "finger_snap" ):
		click(button='right')
	elif( label == "sound_s" ):
		scroll( -250 )
	elif( label == "sound_whistle" ):
		scroll( 250 )
		

winsound.PlaySound('responses/awaitingorders.wav', winsound.SND_FILENAME)
			
audio = pyaudio.PyAudio()
stream = audio.open(format=FORMAT, channels=CHANNELS,
	rate=RATE, input=True,
	frames_per_buffer=CHUNK)

#stream.stop_stream()	
total_frames = []
last_five_probabilities = []
action = ["", 0]
previousProbabilityDict = {}
strategy = "browser"
frames = []
previousIntensity = 0
previousCluckIntensity = 0

# Get a minimum of these elements of data dictionaries
dataDictsLength = 10
dataDicts = []
for i in range( 0, dataDictsLength ):
	dataDict = {}
	for directoryname in data_directory_names:
		dataDict[ directoryname ] = {'percent': 0, 'intensity': 0}
	dataDicts.append( dataDict )
		
while( True ):
	#stream.start_stream()
	frames, intensity = getWavSegment( stream, frames )
	#total_frames.extend( frames )
	#stream.stop_stream()
		
	tempFile = wave.open(TEMP_FILE_NAME, 'wb')
	tempFile.setnchannels(CHANNELS)
	tempFile.setsampwidth(audio.get_sample_size(FORMAT))
	tempFile.setframerate(RATE)
	tempFile.writeframes(b''.join(frames))
	tempFile.close()

	# FEATURE ENGINEERING
	#rawWav = scipy.io.wavfile.read( TEMP_FILE_NAME )[ 1 ]
	fs, rawWav = scipy.io.wavfile.read( TEMP_FILE_NAME )
	chan1 = rawWav[:,0]
	chan2 = rawWav[:,1]
										
	# FFT is symmetrical - Only need one half of it to preserve memory
	ft = fft( chan1 )
	powerspectrum = np.abs( rfft( chan1 ) ) ** 2
	mfcc_result1 = mfcc( chan1, samplerate=fs, nfft=1103 )
	mfcc_result2 = mfcc( chan2, samplerate=fs, nfft=1103 )
	data_row = []
	data_row.extend( mfcc_result1.ravel() )
	data_row.extend( mfcc_result2.ravel() )

	data = [ data_row ]
	
	# Predict the outcome - Only use the result if the probability of being correct is over 50 percent
	probabilities = classifier.predict_proba( data ) * 100
	probabilities = probabilities.astype(int)
	print( probabilities[0] )
	
	# Get the predicted winner
	predicted = np.argmax( probabilities[0] )
	if( isinstance(predicted, list) ):
		predicted = predicted[0]

	probabilityDict = {}
	for index, percent in enumerate( probabilities[0] ):
		label = labelDict[ str( label_array[ index ] ) ]
		probabilityDict[ label ] = { 'percent': percent, 'intensity': int(intensity), 'winner': index == predicted }
		
		if( index == predicted ):
			print( "winner: " + label + " " + str( percent ) )

	dataDicts.append( probabilityDict )
	if( len(dataDicts) > dataDictsLength ):
		dataDicts.pop(0)
		
	# Intensity check
	if( single_tap_detection(dataDicts, "cluck", 35, 1000 ) ):
		click()
	elif( single_tap_detection(dataDicts, "fingersnap", 50, 1000 ) ):
		click(button='right')
	elif( loud_detection(dataDicts, "whistle" ) ):
		scroll( -150 )
	elif( loud_detection(dataDicts, "peak_sound_s" ) ):
		scroll( 150 )
	elif( medium_detection(dataDicts, "bell", 90, 1000 ) ):
		print( 'medium!' )
		hotkey('alt', 'left')
	elif( long_detection(dataDicts, "bell", 80, 1000 ) ):
		print( 'long' )
		press('f4')
		winsound.PlaySound('responses/' + str( random.randint(1,8) ) + '.wav', winsound.SND_FILENAME)
		
		
	#if( probabilityDict[ "bell" ] > 95 and previousProbabilityDict[ "bell" ] < 95 ):
	#	winsound.PlaySound('responses/' + str( random.randint(1,8) ) + '.wav', winsound.SND_FILENAME)
	#	if( strategy == "browser" ):
	#		strategy = "hots"
			#click()
			#hotkey('ctrl', 'f')
			#press('pageup')
	#	elif( strategy == "hots" ):
			#press('esc')
			#press('pagedown')
	#		strategy = "browser"
	
	# Prevent a rise from creating more than one cluck
	#if( probabilityDict["cluck"] > 60 and previousIntensity < intensity ):
	#	previousCluckIntensity = 1
	#else:
	#	previousCluckIntensity = 0
		
	#previousIntensity = intensity
		
	#if( strategy == "browser" ):
	#	for key in enumerate( labelDict.keys() ):
	#		label = str( labelDict[ key[1] ] )
	#		if( ( label == "sound_s" or label == "sound_whistle" ) and continuous_detection( probabilityDict, previousProbabilityDict, label ) ):
	#			press_label( label )
	#		elif( throttled_press_detection( probabilityDict, previousProbabilityDict, label ) ):
	#			press_label( label )
	#elif( strategy == "hots" ):
	#	for key in enumerate( labelDict.keys() ):
	#		label = str( labelDict[ key[1] ] )
	#		if( quick_detection( probabilityDict, previousProbabilityDict, label ) ):
	#			game_label( label )

		
				
	previousProbabilityDict = probabilityDict
	#totalProbabilityMouse = ( probabilityDict["sound_a"] +
	#	probabilityDict["sound_s"] + probabilityDict["sound_ie"] +
	#	probabilityDict["sound_oe"] ) / 4
	#if( totalProbabilityMouse > 10 ):
	#	x = ( probabilityDict["sound_s"] - probabilityDict["sound_a"] ) * 2
	#	y = ( probabilityDict["sound_oe"] - probabilityDict["sound_ie"] ) * 2
	
	#	moveRel( x, y )
			
			
	save_total_file = False
	if( save_total_file and len( total_frames ) > 500 ):
		tempFile = wave.open("audiotest-" + TEMP_FILE_NAME, 'wb')
		tempFile.setnchannels(CHANNELS)
		tempFile.setsampwidth(audio.get_sample_size(FORMAT))
		tempFile.setframerate(RATE)
		tempFile.writeframes(b''.join(total_frames))
		tempFile.close()
	
	