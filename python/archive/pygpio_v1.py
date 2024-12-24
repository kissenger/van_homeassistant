#!/usr/bin/env python
import sys, time, os, logging
from systemd.journal import JournalHandler
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

# -----------------------------------
# CONFIGURE LOGGING TO SYSTEM JOURNAL
# -----------------------------------
logging.basicConfig()
logger = logging.getLogger('pygpio.py')
logger.addHandler(JournalHandler())
logger.setLevel(logging.INFO)
logger.info(" +++ pygpio started")

# -------------- 
# CONFIGURE MQTT
# -------------- 
client = mqtt.Client()
broker_host = "localhost"
broker_port =  1883
topics = [("lights/#",0),("pygpio/#",0)]

# --------------
# CONFIGURE GPIO
# --------------
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
lights=[
   {"location": "ceiling", "pin":  5, "state": 0},
   {"location": "table",   "pin":  6, "state": 0},
   {"location": "beds",    "pin": 13, "state": 0},
   {"location": "fairy",   "pin": 19, "state": 0},
   {"location": "outside", "pin": 26, "state": 0}
]
for index,light in enumerate(lights):
   print(light)
   GPIO.setup(light["pin"],GPIO.OUT)
   light.update({"pwm": GPIO.PWM(light["pin"],5000)})
   light["pwm"].start(50)
   light["state"]=50

# --------------------
# SET GLOBAL VARIABLES
# --------------------
led_brightness = 100

# ===============================================================

# -------------------------
# SET PWM FOR SUPPLIED PINS
# -------------------------
def set_light(location,command):
   global lights
   global led_brightness
   dc = 0 if command == "OFF" else led_brightness
   for light in lights:
      if light["location"] == location:
         light["pwm"].ChangeDutyCycle(dc)
         light["state"]=dc
         logger.info(" +++ Duty cycle for " + location + " light on pin " + str(light["pin"]) + " set to " + str(dc) + "%")

def set_all_lights(command):
   global lights
   for light in lights: 
      set_light(light["location"],command)

def set_brightness(dc):
   global led_brightness, lights
   led_brightness=dc
   client.publish("lights/brightness/state",dc,qos=0,retain=True)
   for light in lights:
      if light["state"] != 0:
         light["pwm"].ChangeDutyCycle(dc)
         logger.info(" +++ PWM duty cycle for " + light["location"] + " light set to " + str(dc) + "%")

# -------------------------
# PROCESS INCOMING MESSAGES
# -------------------------
def on_message(client, userdata, msg):

   topic = msg.topic.split("/") 
   payload = msg.payload.decode("utf-8")
   logger.info(" +++ received message: topic=" + msg.topic + " payload=" + payload)

   if topic[0] == "lights":
      if topic[1] == "brightness":
         if topic[2] == "set":
           set_brightness(payload)
      else: 
         set_light(topic[1],payload)

   if topic == "pygpio/hello":
      logger.info(" +++ publishing to: gpio/available")
      client.publish("gpio/available","online",qos=0,retain=True)

# ----------------------------
# CALLBACK FOR MQTT CONNECTION
# ----------------------------
def on_connect(client, userdata, flags, rc):
   if rc == 0:
      logger.info(" +++ connected to mosquitto host")
      client.publish("gpio/available","online")
      client.subscribe(topics)
      set_all_lights("OFF")
   else:
      logger.info(" +++ failed to connect with code %d\n", rc)

# -------------------------------
# CALLBACK FOR MQTT DISCONNECTION
# -------------------------------
def on_disconnect(client, userdata, rc):
   logger.info(" +++ disconnected from mosquitto host")

# ===============================================================

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.connect(broker_host, broker_port, 60)
client.loop_start()

while True:
   try: 
      time.sleep(0.1)
   except KeyboardInterrupt:
      logger.info(" +++ keyboard interrupt - cleaning up")
      for light in lights:
         light["pwm"].stop()
         GPIO.setup(light["pin"],GPIO.OUT)
         GPIO.output(light["pin"],GPIO.LOW) 
      client.publish("gpio/available","offline")
      client.disconnect(13)
      client.loop_stop()
      print("stop")
      GPIO.cleanup()
      sys.exit(os.EX_OK)
