import speech_recognition as sr
from time import ctime
import time
import math
import os
import re
from gtts import gTTS
import serial


###init & configure

#replace yourpathhere with working directory & baudrate (default at 9600)
ser = serial.Serial('yourpathhere', baudrate=9600, bytesize=8)
time.sleep(3)

#Command to activate steppers: M17 by default
ser.write(b'M17\r')

#xyz at home position (see pdf for robot geometry)
homex = 0
homey = 19.5
homez = 134

#define 3 commands: go (straight line), grip & ungrip
go = "G0"
grip = "M3"
ungrip = "M4"

commandType = go

#global variable xyz to keep track of current xyz
xyz = [homex, homey, homez]

#list for memory locations (retrival command to be written by user)
memXyz = []

#max reach when z=0
maxreach = 220

#standby position height & hypotenuse length
standbyZ = 120
standbyHP = 120

#move to standbyZ at current angle
def standby():
	global xyz
	#hypotenuse based on xy
	hp = math.sqrt(xyz[0]**2 + xyz[1]**2)
	#degree based on current xy location: initialize at 0, range -90 to 90
	orad = math.asin(xyz[0]/hp)
	xyz[0] = math.sin(orad) * standbyHP
	xyz[1] = math.cos(orad) * standbyHP
	xyz[2] = standbyZ

#return point of furthest reach based on any xy point
def reachout():
	global xyz
	#hypotenuse based on xy
	hp = math.sqrt(xyz[0]**2 + xyz[1]**2)
	#degree based on current xy location: initialize at 0, range -90 to 90
	orad = math.asin(xyz[0]/hp)
	xyz[0] = math.sin(orad) * maxreach
	xyz[1] = math.cos(orad) * maxreach
	xyz[2] = 0

#rotate at specific angle clockwise or counter clockwise
def rotate(deg, clock):
	global xyz
	#hypotenuse based on xy
	hp = math.sqrt(xyz[0]**2 + xyz[1]**2)
	#degree based on current xy location: initialize at 0, range -180 to 180
	orad = math.asin(xyz[0]/hp)
	print('now at: ' + str(math.degrees(orad)))

	#clock = 1 in clockwise & clock = 0 in counterclockwise
	nrad = orad - math.radians(deg) if clock == 0 else orad + math.radians(deg)
	print('clockwise') if clock == 1 else print('counterclockwise')
	print(math.degrees(nrad))

	xyz[0] = math.sin(nrad) * hp
	xyz[1] = math.cos(nrad) * hp 

#move in a straight line given lenght and direction (str)
def move(length, dir):
	global xyz
	hp = math.sqrt(xyz[0]**2 + xyz[1]**2)

	if dir == 'up':
		xyz[2] = xyz[2] + length
	if dir == 'down':
		xyz[2] = xyz[2] - length
	if dir == 'back':
		hpratio = (hp - length) / hp
		xyz[0] = xyz[0] * hpratio
		xyz[1] = xyz[1] * hpratio
	if dir == 'forward':
		hpratio = (hp + length) / hp
		xyz[0] = xyz[0] * hpratio
		xyz[1] = xyz[1] * hpratio
	if dir == 'left':
		xyz[0] = xyz[0] + length
	if dir == 'right':
		xyz[0] = xyz[0] - length

#voice reply per user definition
def speak(outputString):
    print(outputString)
    tts = gTTS(text=outputString, lang='en')
    tts.save("temp.mp3")
    os.system("mpg321 temp.mp3")

#voice reply in saved replies
def play(soundReply):
	systemName = "mpg321 " + soundReply + ".mp3"
	os.system(systemName)

#check if number in string
def hasNum(data):
	return any(i.isdigit() for i in data)

#identify number in string and return first occurence
def extractnum(inputString):
	extractlist = re.findall(r"[-+]?\d*\.\d+|\d+", inputString)
	return float(extractlist[0])

#record audio and return string for looping
def recordAudio():
    # Record Audio
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Give me an order")
        audio = r.listen(source)
 
    # Speech recognition using Google Speech Recognition
    data = ""
    try:
        # Uses the default API key
        # To use another API key: `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
        data = r.recognize_google(audio)
        print("You said: " + data)
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
    except sr.RequestError as e:
        print("Could not request results from Google Speech Recognition service; {0}".format(e))
 
    return data

#save current location to memory list memXyz
def remember():
	global memXyz
	memXyz.append(xyz)

#retrive last saved item from memXyz and assign as current location
def retriveMemory():
	global xyz
	xyz = memXyz[-1]

#return gcode in byte format 
def gcode():
	if commandType == go:
		gcodestr = commandType + ' X' + str(xyz[0]) + ' Y' + str(xyz[1]) + ' Z' + str(xyz[2]) + '\r'
	else:
		gcodestr = commandType + '\r'
	gcodebyte = gcodestr.encode('ASCII')
	print(gcodebyte)
	return gcodebyte

#library for keyword recognition
def translateCommand(data):
	global xyz
	global memXyz
	global commandType
	
	if "remember" in data or "save" in data:
		remember()
		play("save")

	if "memory" in  data:
		retriveMemory()
		play("memoryretrived")
		return True

	if "stand by" in data or "easy" in data:
		standby()
		play("standby")
		return True

	if "reach out" in data or "extend" in data:
		reachout()
		play("reachout")
		return True

	if "home" in data or "attention" in data:
		xyz = [homex, homey, homez]
		play("homing")
		return True

	if "rotate" in data:
		deg = extractnum(data) if hasNum(data) else 0
		cw = 0 if "counterclockwise" in data else 1
		rotate(deg, cw)
		play("turning")
		return True

	#move per direction per user definition, default 5mm if no number identified
	if "go" in data:
		length = extractnum(data) if hasNum(data) == True else 5
		if "up" in data:
			move(length, "up")
		if "down" in data:
			move(length, "down")
		if "forward" in data:
			move(length, "forward")
		if "back" in data:
			move(length, "back")
		if "left" in data:
			move(length, "left")
		if "right" in data:
			move(length, "right")
		return True 

	if "catch" in data or "hold" in data or "grab" in data:
		commandType = grip
		return True

	if "release" in data or "let go" in data:
		commandType = ungrip
		return True

	if "thank you" in data:
		speak("You are welcome")

	if "well done" in data or "good job" in data:
		play("thankyou")

	#report current location
	if "report" in data:
		if "location" in data:
			speak("X" + str(xyz[0]) + " Y" + str(xyz[1]) + " Z" + str(xyz[2]))
	return False

while 1:
    data = recordAudio()
    if translateCommand(data.lower()) != False:
	    ser.write(gcode())
	    commandType = go
	    time.sleep(0.5)




