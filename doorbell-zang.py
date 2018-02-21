import os
import httplib, urllib
import RPi.GPIO as GPIO
import time, sys
import soco
from datetime import date
from soco import SoCo
from soco.snapshot import Snapshot
from multiprocessing import Process
from zang.exceptions.zang_exception import ZangException
from zang.configuration.configuration import Configuration
from zang.connectors.connector_factory import ConnectorFactory
from docs.examples.credentials import sid, authToken
url = 'http://api.zang.io/v2'
configuration = Configuration(sid, authToken, url=url)
smsMessagesConnector = ConnectorFactory(configuration).smsMessagesConnector

#switch pins set using built in pull up resistor plus a hardware 10K resistor to ground
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#color pins set by GPIO.BCM
redPin = 17
greenPin = 22
bluePin = 27

#setting code for colors, can customize for your own colours
#output uses GPIO.LOW because my LED is an anode
def turnOn(pin):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

def turnOff(pin):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)

def cyanOn():
    turnOn(greenPin)
    turnOn(bluePin)
    turnOff(redPin)

def whiteOn():
    turnOn(redPin)
    turnOn(greenPin)
    turnOn(bluePin)
#Sonos code is here for snapshot activating speakers for doorbell
def play_alert(zones, alert_uri, alert_volume=60, alert_duration=0, fade_back=True):
    # Use soco.snapshot to capture current state of each zone to allow restore
    for zone in zones:
        zone.snap = Snapshot(zone)
        zone.snap.snapshot()
        print('snapshot of zone: {}'.format(zone.player_name))

    # prepare all zones for playing the alert
    for zone in zones:
        # Each Sonos group has one coordinator only these can play, pause, etc.
        if zone.is_coordinator:
            if not zone.is_playing_tv:  # can't pause TV - so don't try!
                # pause music for each coordinators if playing
                trans_state = zone.get_current_transport_info()
                if trans_state['current_transport_state'] == 'PLAYING':
                    zone.pause()

        # For every Sonos player set volume and mute for every zone
        zone.volume = alert_volume
        zone.mute = False

    # play the sound (uri) on each sonos coordinator
    print('will play: {} on all coordinators'.format(alert_uri))
    for zone in zones:
        if zone.is_coordinator:
            zone.play_uri(uri=alert_uri, title='Sonos Alert')

    # wait for alert_duration
    time.sleep(alert_duration)

    # restore each zone to previous state
    for zone in zones:
        print('restoring {}'.format(zone.player_name))
        zone.snap.restore(fade=fade_back)

if __name__ == '__main__':

    all_zones = soco.discover()
    # alert uri to send to sonos - this uri must be available to Sonos
    alert_sound = 'http://front-door.ddns.net:8080/doorbell2.wav'

#doorbell sound play through sonos
def play_doorbell():
    play_alert(all_zones, alert_sound, alert_volume=50, alert_duration=2, fade_back=True)

#call phone through SIP
def call_phone():
    os.system('sh /home/pi/doorbell/phone-zang.sh')

#here is the logic for the doorbell
if __name__=='__main__':
     whiteOn()
     while True:
         input_state = GPIO.input(23)
         if input_state == False:
            print('Someone is at the door!\r')
	    try:
    		smsMessage = smsMessagesConnector.sendSmsMessage(
        		to='14168305230',
        		body='Someone is at the door!',
        		from_='16477992796')
    	      	print(smsMessage)
	    except ZangException as e:
              	print(e)
            cyanOn()
       #sonos play sound for doorbell, calling sip phone and push notification
	    p3 = Process(target = call_phone)
	    p2 = Process(target = play_doorbell)
	    p3.start()
            p2.start()
	    time.sleep(5)
            whiteOn()
