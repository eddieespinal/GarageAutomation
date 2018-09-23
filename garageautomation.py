"""Python script to monitor and control garage doors via SMS and a Raspberry Pi."""
"""Created by: Eddie Espinal - May 3, 2018 -  http://instagram.com/4hackrr"""

import os
import datetime
import time
import httplib
import email.utils
import RPi.GPIO as GPIO

from time import sleep, strftime
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from dotenv import load_dotenv
from enum import Enum
from dateutil import parser
import picamera
from picamera import Color
from fractions import Fraction
import pyimgur

import paho.mqtt.client as mqtt


# Setup Environment Variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Setup GPIO
IRSENSORPIN = 17
RELAYPIN = 18

GPIO.setmode(GPIO.BCM)    
GPIO.setup(IRSENSORPIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(RELAYPIN, GPIO.OUT)
GPIO.output(RELAYPIN, GPIO.HIGH)

alarmTriggerTime = "11:00 PM"
notificationDelayInSeconds = 300 # five minutes in seconds
GARAGE_OPEN_CLOSE_DELAY = 5 # five seconds

IMG_WIDTH = 640
IMG_HEIGHT = 480
IMAGE_PATH = "/home/pi/GarageAutomation/image.jpg"

# initialize imgur 
# imgur client setup
CLIENT_ID = os.getenv("IMGUR_CLIENT_ID")
imgur = pyimgur.Imgur(CLIENT_ID)

validCommands = ["open", "close", "status", "photo", "reboot", "shutdown"]

class DoorStatus(Enum):
    OPEN = 0 
    CLOSED = 1 
    UNKNOWN = 2

class GarageAutomation():
    def __init__(self):
        self.client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
        self.toNumber = os.getenv("TO_NUMBER")
        self.fromNumber = os.getenv("TWILIO_NUMBER")
        self.doorStatus = DoorStatus.UNKNOWN
        self.lastSentNoticationTime = -1
        self.garageAutomaticallyClosed = False

        # setup the mqtt client
        self.mqttClient = mqtt.Client()
        self.mqttClient.on_message = self.on_message
        self.mqttClient.on_connect = self.on_connect
        self.mqttClient.on_disconnect = self.on_disconnect
        self.mqttClient.username_pw_set(os.getenv("CLOUD_MQTT_USER"), password=os.getenv("CLOUD_MQTT_PASSWORD"))
        # connect
        self.mqttClient.connect(os.getenv("CLOUD_MQTT_SERVER"), int(os.getenv("CLOUD_MQTT_PORT")))
        self.mqttClient.subscribe("garage/command/#", qos=1)

        # Send a SMS when the system starts. This will be used when automaticaly restarting the Pi to make sure is working
        self.sendSystemStartedNotification()

    # # MQTT functions
    def on_connect(self, client, userdata, flags, rc):
        print("MQTT connected with code %d." % (rc))

    def on_disconnect(self, client, userdata, rc):
        print("MQTT disconnect: %s" % mqtt.error_string(rc))

    def on_subscribe(self, client, userdata, mid, granted_qos):
        print("Subscribed: "+str(mid)+" "+str(granted_qos))
 
    def on_message(self, client, userdata, msg):
        print(msg.topic+" "+str(msg.qos)+" "+str(msg.payload))
        
        # Grab the command from the payload
        command = str(msg.payload).lower()
  
        # Let's make sure we are not processing invalid commands
        if command in validCommands:
            if command == 'close':
                # call the close garage command here
                self.openCloseDoor(DoorStatus.CLOSED)
                self.sendNotificationsMessage("Executed - Garage Close Command")
                time.sleep(GARAGE_OPEN_CLOSE_DELAY)
                self.sendImageViaSMS()

            if command == 'open':
                # call the open garage command here
                self.openCloseDoor(DoorStatus.OPEN)
                self.sendNotificationsMessage("Executed - Garage Open Command")
                time.sleep(GARAGE_OPEN_CLOSE_DELAY)
                self.sendImageViaSMS()

            if command == 'status':
                # call the garage status command here
                doorStatusString = "CLOSED"
                if self.doorStatus == DoorStatus.OPEN:
                    doorStatusString = "OPEN"

                self.sendNotificationsMessage("The garage door is currently {}".format(doorStatusString))

            if command == 'photo':
                self.sendNotificationsMessage("Requesting photo, please wait...")
                # take a photo and send it via SMS
                self.captureSendImage()
            
            if command == 'reboot':
                self.sendNotificationsMessage("Executed - Reboot Command")
                os.system('sudo shutdown -r now')

            if command == 'shutdown':
                self.sendNotificationsMessage("Executed - Shutdown Command")
                os.system('sudo shutdown -h now')

            time.sleep(5) 

    def sendSystemStartedNotification(self):
        #self.sendNotificationsMessage("Garage Automation Started")
        self.logStatus("Garage Automation Started")

    def reset(self):
        self.lastSentNoticationTime = -1
        self.doorStatus = DoorStatus.UNKNOWN
        self.garageAutomaticallyClosed = False

    def captureSendImage(self):
        dateString = datetime.datetime.now().strftime("%m-%d-%Y %-I:%M:%S %p")
        with picamera.PiCamera() as camera:
            camera.annotate_text = dateString
            self.configureCamera(camera)
            camera.capture(IMAGE_PATH)
            
        uploaded_image = imgur.upload_image(IMAGE_PATH, title=dateString)

        doorStatusString = "CLOSED"
        if self.doorStatus == DoorStatus.OPEN:
            doorStatusString = "OPEN"

        self.sendNotificationsMessage("The garage door is currently {}".format(doorStatusString), uploaded_image.link)

    def configureCamera(self, camera):
        camera.annotate_foreground = Color('white')
        camera.annotate_background = Color('black')
        camera.resolution = (IMG_WIDTH, IMG_HEIGHT)
        if self.doorStatus == DoorStatus.CLOSED:
            camera.contrast = 100
            camera.brightness = 80
            camera.framerate = Fraction(1, 6)
            camera.iso = 800
            camera.exposure_mode = 'night'
            camera.shutter_speed = 4000000
            time.sleep(5)

    def sendImageViaSMS(self):
        dateString = datetime.datetime.now().strftime("%m-%d-%Y %-I:%M:%S %p")
        with picamera.PiCamera() as camera:
            camera.annotate_text = dateString
            self.configureCamera(camera)
            camera.capture(IMAGE_PATH)
        uploaded_image = imgur.upload_image(IMAGE_PATH, title=dateString)
        self.sendNotificationsMessage(dateString, uploaded_image.link)

    def getDoorStatus(self):
        if (GPIO.input(IRSENSORPIN) == 0):
            self.doorStatus = DoorStatus.OPEN
        if (GPIO.input(IRSENSORPIN) == 1):
            self.doorStatus = DoorStatus.CLOSED
        return self.doorStatus

    def openCloseDoor(self, doorStatus):
        print "Received command to {} the door".format("OPEN" if doorStatus == DoorStatus.OPEN else "CLOSE")
        
        if doorStatus == DoorStatus.OPEN:
            self.logStatus("OPEN")
        else:
            self.logStatus("CLOSE")
        
        GPIO.output(RELAYPIN, GPIO.LOW)
        time.sleep(1)
        GPIO.output(RELAYPIN, GPIO.HIGH)

    def sendNotificationsMessage(self, messageBody, media_url=None):
        try: 
            if media_url is not None:
                self.client.messages.create(from_=self.fromNumber, to=self.toNumber, body=messageBody, media_url=media_url)
            else:
                self.client.messages.create(from_=self.fromNumber, to=self.toNumber, body=messageBody)
        except TwilioRestException as e: 
            print(e)

    def checkIfGarageDoorIsOpenedPastTriggerTime(self):
        now = datetime.datetime.now().strftime("%I:%M %p")
        dt = datetime.datetime.now().timetuple()
        alarmTriggerTimeObject = parser.parse(alarmTriggerTime) # returns 23:00 in 24hr format

        if (dt.tm_hour == alarmTriggerTimeObject.hour and dt.tm_min == alarmTriggerTimeObject.minute) and self.doorStatus == DoorStatus.OPEN:
            if self.lastSentNoticationTime < 0 :
                print("Warning, Garage Doors are Opened Past Trigger Time")
                self.lastSentNoticationTime = time.time()
                self.sendNotificationsMessage("Warning, The garage door is opened, reply `Close` to automatically close it")
                self.logStatus("OPEN")

        # If the notification was already sent and the garage still opened, let's wait 5 minutes before closing the garage automatically.
        if (dt.tm_hour == alarmTriggerTimeObject.hour and dt.tm_min > alarmTriggerTimeObject.minute) and (time.time() - self.lastSentNoticationTime > notificationDelayInSeconds) and self.doorStatus == DoorStatus.OPEN and not self.garageAutomaticallyClosed:
            print("Automatically closing the garage")
            self.logStatus("Automatically closing the garage")
            self.openCloseDoor(DoorStatus.CLOSED)
            self.sendNotificationsMessage("The garage door was automatically closed at {}".format(now))
            self.garageAutomaticallyClosed = True
        elif dt.tm_hour > alarmTriggerTimeObject.hour and self.lastSentNoticationTime > 0:
            print("Resetting stored flags")
            self.reset()

    def logStatus(self, garageStatus):
        with open("garage_status_log.csv", "a") as log:
            log.write("{0},{1}\n".format(datetime.datetime.now().strftime("%m-%d-%Y %-I:%M:%S %p"),str(garageStatus)))
            sleep(1)

    def run(self):
        try:
            # Continue the network loop, exit when an error occurs
            rc = 0
            while rc == 0:
                rc = self.mqttClient.loop()
                self.getDoorStatus()
                self.checkIfGarageDoorIsOpenedPastTriggerTime()
                sleep(1)
            print("rc: " + str(rc)) 
        finally:
            GPIO.cleanup() # ensures a clean exit


if __name__ == "__main__":
    try:
        print("Starting Garage Automation System")
        garageAutomation = GarageAutomation()
        garageAutomation.run()
    # End program cleanly with keyboard  
    except KeyboardInterrupt:  
        print "Quit"  