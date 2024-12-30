#!/usr/bin/env python
import glob, sys, time, os, logging
import paho.mqtt.client as mqtt
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import PWMOutputDevice
from systemd.journal import JournalHandler

# -----------------------------------
# CONFIGURE LOGGING TO SYSTEM JOURNAL
# -----------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('pygpio')
logger.propagate = False
logger.addHandler(JournalHandler())
logger.info(" +++ pygpio started")

# -------------- 
# CONFIGURE MQTT
# -------------- 
client = mqtt.Client()
broker_host = "localhost"
broker_port =  1883
topics = [("lights/#",0),("pygpio/ping",0)]

# --------------
# CONFIGURE GPIO
# --------------
lights={
   "ceiling": {"pin": 5 , "state": 0, "dimmable": True},
   "table":   {"pin": 6 , "state": 0, "dimmable": True},
   "beds":    {"pin": 13, "state": 0, "dimmable": True},
   "fairy":   {"pin": 19, "state": 0, "dimmable": False},
   "outside": {"pin": 26, "state": 0, "dimmable": False},
}

for light in lights:
   lights[light].update({"pwm": PWMOutputDevice(lights[light]["pin"],frequency=500,pin_factory=PiGPIOFactory())})

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
   lights[location]["pwm"]  =int(dc)/100
   lights[location]["state"]=int(dc)/100
   publish_message("lights/state/" + location,command)
   logger.info(" +++ duty cycle for " + location + " light on pin " + str(lights[location]["pin"]) + " set to " + str(int(dc)/100))

def set_all_lights(command):
   global lights
   for light in lights: 
      set_light(light,command)

def set_brightness(dc):
   global led_brightness, lights
   led_brightness=dc
   publish_message("lights/state_brightness",dc)
   for light in lights:
      if (lights[light]["state"] != 0) and (lights[light]["dimmable"] == True):
         set_light(light,"ON")

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
      publish_message("temperature/" + sensor + "/value", temperature);
   
# -------------------------
# PROCESS INCOMING MESSAGES
# -------------------------
def on_message(client, userdata, msg):
   logger.info(" +++ received topic=" + msg.topic + " payload=" + str(msg.payload))

   # catch request for availability
   if msg.topic == "pygpio/ping":
      publish_message("gpio/available","online")
   
   topic = msg.topic.split("/") 
   device = topic[0]
   action = topic[1]
   try:
      location = topic[2]
   except:
      pass 
   payload = msg.payload.decode("utf-8")

   if device == "lights":
      if action == "set_brightness":
         set_brightness(payload)
      elif action == "set_state":
         if location == "all":
            set_all_lights(payload)
         else: 
            set_light(location,payload)

def publish_message(topic, payload):
   client.publish(topic, payload,qos=2,retain=True)
   logger.info(" +++ published topic=" + topic + ", payload=" + str(payload))
	
# ----------------------------
# CALLBACK FOR MQTT CONNECTION
# ----------------------------
def on_connect(client, userdata, flags, rc):
   if rc == 0:
      logger.info(" +++ connected to mosquitto host")
      publish_message("gpio/available","online")
      client.subscribe(topics)
      set_brightness(100)
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
      publish_message("gpio/available","offline")
      time.sleep(0.1)
      client.disconnect(13)
      client.loop_stop()
      sys.exit(os.EX_OK)
