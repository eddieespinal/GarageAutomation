# GarageAutomationRaspberryPi
Automate my garage using a Raspberry Pi 3 B+

![Garage Automation](https://image.ibb.co/fCrSzS/IMG_4211_2.jpg)

## Parts Needed

* [Raspberry Pi 3 B, B+](https://www.adafruit.com/product/3775)
* [2-Channel Relay](https://www.amazon.com/SunFounder-Channel-Optocoupler-Expansion-Raspberry/dp/B00E0NTPP4/ref=sr_1_2?ie=UTF8&qid=1525619045&sr=8-2&keywords=2-channel+relay) (or Any compatible relay)
* [IR Break Beam Sensor](https://www.amazon.com/Adafruit-IR-Break-Beam-Sensor/dp/B00XW2NVJU/ref=sr_1_1?s=electronics&ie=UTF8&qid=1525619158&sr=1-1&keywords=IR+Break+Beam+Sensor+-+5mm+LEDs)
* [Project box plastic enclosure](https://www.amazon.com/Hammond-1591ESBK-ABS-Project-Black/dp/B0002BSRIO/ref=sr_1_3?ie=UTF8&qid=1525620343&sr=8-3&keywords=project+box+enclosure)
* Garage remote (optional)

## Requirement
* [Twilio](https://www.twilio.com) Account for sending & receiving SMS messages.

# Setup

Clone this repository in your home directory of the Raspberry Pi

```
git clone https://github.com/eddieespinal/GarageAutomation.git
```

You need to setup a virtual enviroment to install the dependancies that are required for this project.

Make sure you are inside the GarageAutomation directory
```
cd GarageAutomation
```

Install the [virtualenv library](https://virtualenv.pypa.io/en/stable/)
```
pip install virtualenv
```

Now create a virtual environment called `venv`
```
virtualenv venv
```

Now you need to activate this new virtual environment
```
source venv/bin/activate
```

# Install Dependancies
There is a file called `requirements.txt` inside the `GarageAutomation` folder.  Run the following command to install the dependancies listed there.

```
pip install -r requirements.txt
```

Go inside the `GarageAutomation` directory and create a copy of the .env-sample and name it .env
```
cd GarageAutomation
```

Make a copy of `.env-sample` and name it `.env`
```
mv .env-sample .env
```

# Configurations
Edit the .env file with your own settings from Twilio. Replace `YOUR_AUTH_TOKEN` and `YOUR_ACCOUNT_SID` with your own.  Also enter your own `TWILIO_NUMBER`, this will be used as the From number when sending messages from the Raspberry Pi.

```
sudo nano .env
```
```javascript
TWILIO_ACCOUNT_SID="YOUR_ACCOUNT_SID"
TWILIO_AUTH_TOKEN="YOUR_AUTH_TOKEN"
TWILIO_NUMBER="+18009997777"
TO_NUMBER="+18006663333"
```

Save your changes by pressing `Control+x`, then `Y` then `Enter`


Edit the `garageautomation.py` file and configure the time you want the garage to automatically notify you and the duration before automatically closing itself. 

```
sudo nano garageautomation.py
```

```python
alarmTriggerTime = "11:00 PM"
notificationDelayInSeconds = 300 # five minutes in seconds
```

Save your changes by pressing `Control+x`, then `Y` then `Enter`

This means that the garage will notify you at **11:00 PM** if the door is opened via SMS.  If you don't reply back with the `Close` comand it will automatically close itself **5 minutes** from the time you got notified.

## Setup GPIO
You can change these values only if you don't want to use the same pins for the relay and the IR sensor. You can use the following image for reference.
```python
IRSENSORPIN = 17
RELAYPIN = 18
```
![Raspberry Pi Pinout](https://i2.wp.com/randomnerdtutorials.com/wp-content/uploads/2018/01/RPi-Pinout.jpg)


# Automatically run this script when the Raspberry Pi boot
In order to fully automate this project, we need to make sure that when the Raspberry start it runs the garageautomation.py script. Edit the following file to do that.
```
sudo nano /etc/rc.local 
```
Copy and paste the following command at the end of this file but before `exit 0`.
```
(sleep 10; . /home/pi/GarageAutomationRaspberryPi/venv/bin/activate; python /home/pi/GarageAutomationRaspberryPi/garageautomation.py)&
```

# Project Photos
![Garage Automation](https://image.ibb.co/k7cd67/IMG_4181.jpg)

![Garage Automation](https://image.ibb.co/dTm5m7/IMG_4162.jpg)

![Garage Automation](https://image.ibb.co/iDB5m7/IMG_4223.jpg)

![Garage Automation](https://image.ibb.co/hqr5m7/IMG_4219.jpg)