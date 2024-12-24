#!/usr/bin/env python
import glob, sys, time, os, logging
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import PWMOutputDevice
from systemd.journal import JournalHandler

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
lights=[
   {"location": "ceiling", "pin":  5, "state": 0},
   {"location": "table",   "pin":  6, "state": 0},
   {"location": "beds",    "pin": 13, "state": 0},
   {"location": "fairy",   "pin": 19, "state": 0},
   {"location": "outside", "pin": 26, "state": 0}
]
for index,light in enumerate(lights):
   print(light)
   light.update({"pwm": PWMOutputDevice(light["pin"],frequency=500,pin_factory=PiGPIOFactory())})

# -----------------
# Configure DS18B20
# -----------------
temp_sensors={
   "fridge"     : {"device_file": "/sys/bus/w1/devices/28-00000a08b0ad/w1_slave"},
   "fridge_vent": {"device_file": "/sys/bus/w1/devices/28-00000a0a9e13/w1_slave"},
}

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

# --------------------
# SET GLOBAL VARIABLES
# --------------------
led_brightness = 1

# ===============================================================

# ------------------------
# FUNCTIONS FOR LED LIGHTS 
# ------------------------
def set_light(location,command):
   global lights
   global led_brightness
   dc = 0 if command == "OFF" else led_brightness
   for light in lights:
      if light["location"] == location:
         light["pwm"].value=int(dc)/100
         light["state"]=int(dc)/100
         logger.info(" +++ Duty cycle for " + location + " light on pin " + str(light["pin"]) + " set to " + str(int(dc)/100))

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
         set_light(light["location"],"ON")

# ---------------------
# FUNCTIONS FOR DS18B20 
# Ref: https://randomnerdtutorials.com/raspberry-pi-ds18b20-python/
# ---------------------
def read_temp(device_file):
   f=open(device_file,'r')
   lines=f.readlines()
   f.close()
   while lines[0].strip()[-3:] != 'YES':
       time.sleep(0.2)
       lines = read_temp_raw()
   equals_pos = lines[1].find('t=')
   if equals_pos != -1:
       temp_string = lines[1][equals_pos+2:]
       temp_c = float(temp_string) / 1000.0
       return temp_c

def get_temperatures():
   global temp_sensors
   for sensor in temp_sensors:
      temperature = read_temp(temp_sensors[sensor]["device_file"])
      client.publish("temperature/" + sensor, temperature);
      logger.info(" +++ published message: topic=temperature/" + sensor + " payload=" + str(temperature))
   
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
      set_brightness(50)
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
      get_temperatures()
      time.sleep(10)
   except KeyboardInterrupt:
      logger.info(" +++ keyboard interrupt - cleaning up")
      set_all_lights("OFF")
      client.publish("gpio/available","offline")
      client.disconnect(13)
      client.loop_stop()
      sys.exit(os.EX_OK)
