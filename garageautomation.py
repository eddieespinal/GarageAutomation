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
# from picamera import PiCamera
import pyimgur

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



IMG_WIDTH = 800
IMG_HEIGHT = 600
IMAGE_PATH = "/home/pi/GarageAutomation/image.jpg"

# camera = PiCamera()

# initialize imgur 
# imgur client setup
CLIENT_ID = os.getenv("IMGUR_CLIENT_ID")
imgur = pyimgur.Imgur(CLIENT_ID)

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

    def reset(self):
        self.lastSentNoticationTime = -1
        self.doorStatus = DoorStatus.UNKNOWN

    def captureSendImage(self):
        dateString = datetime.datetime.now().strftime("%m-%d-%Y %-I:%M:%S %p")
        # camera.annotate_text = dateString
        # camera.resolution = (IMG_WIDTH, IMG_HEIGHT)
        # camera.capture(IMAGE_PATH)
        os.system("raspistill -o /home/pi/GarageAutomation/image.jpg")
        uploaded_image = imgur.upload_image(IMAGE_PATH, title=dateString)

        doorStatusString = "CLOSED"
        if self.doorStatus == DoorStatus.OPEN:
            doorStatusString = "OPEN"

        self.sendNotificationsMessage("The garage door is currently {}".format(doorStatusString), uploaded_image.link)

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

        if now == alarmTriggerTime and self.doorStatus == DoorStatus.OPEN:
            if self.lastSentNoticationTime < 0 :
                print("Warning, Garage Doors are Opened Past Trigger Time")
                self.lastSentNoticationTime = time.time()
                self.sendNotificationsMessage("Warning, The garage door is opened, reply `Close` to automatically close it")
                self.logStatus("OPEN")

        # If the notification was already sent and the garage still opened, let's wait 5 minutes before closing the garage automatically.
        if (dt.tm_hour == alarmTriggerTimeObject.hour and dt.tm_min > alarmTriggerTimeObject.minute) and (time.time() - self.lastSentNoticationTime >= notificationDelayInSeconds) and self.doorStatus == DoorStatus.OPEN:
            print("Automatically closing the garage")
            self.logStatus("Automatically closing the garage")
            self.openCloseDoor(DoorStatus.CLOSED)
            self.sendNotificationsMessage("The garage door was automatically closed at {}".format(now))
        elif dt.tm_hour > alarmTriggerTimeObject.hour:
            print("Resetting stored flags")
            self.reset()
       

    def listenForSMSCommand(self):
        try:
            messages = self.client.messages.list(to=self.fromNumber,from_=self.toNumber,date_sent=datetime.datetime.utcnow())

            for message in messages:
                print "Message Body: {} - Date: {}".format(message.body.lower(), message.date_sent)
                if message.status == 'received':
                # select only recently sent messages were time now less time sent is very small
                # (removing an amount from datetime.utcnow() allows the message to be retreived for on a few seconds.
                    date_sent = message.date_sent.strftime('%a, %d %b %Y %H:%M:%S+0000')
                    if (time.mktime(datetime.datetime.utcnow().timetuple())-21602) < email.utils.mktime_tz(email.utils.parsedate_tz(date_sent)):

                        if message.body.lower() == 'close':
                            # call the close garage command here
                            self.openCloseDoor(DoorStatus.CLOSED)
                            self.sendNotificationsMessage("Executed - Garage Close Command")

                        if message.body.lower() == 'open':
                            # call the open garage command here
                            self.openCloseDoor(DoorStatus.OPEN)
                            self.sendNotificationsMessage("Executed - Garage Open Command")

                        if message.body.lower() == 'status':
                            # call the garage status command here
                            doorStatusString = "CLOSED"
                            if self.doorStatus == DoorStatus.OPEN:
                                doorStatusString = "OPEN"

                            self.sendNotificationsMessage("The garage door is currently {}".format(doorStatusString))

                        if message.body.lower() == 'photo':
                            # take a photo and send it via SMS
                            self.captureSendImage()

                        time.sleep(5)

        except TwilioRestException as e:
            print(e)

    def logStatus(self, garageStatus):
        with open("garage_status_log.csv", "a") as log:
            log.write("{0},{1}\n".format(datetime.datetime.now().strftime("%m-%d-%Y %-I:%M:%S %p"),str(garageStatus)))
            sleep(1)

    def run(self):
        while (True):
            self.getDoorStatus()
            self.checkIfGarageDoorIsOpenedPastTriggerTime()
            self.listenForSMSCommand()



if __name__ == "__main__":
    try:
        print("Starting Garage Automation System")
        garageAutomation = GarageAutomation()
        garageAutomation.run()
    # End program cleanly with keyboard  
    except KeyboardInterrupt:  
        print "Quit"  
        # Reset GPIO settings  
        GPIO.cleanup() 