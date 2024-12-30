from evdev import InputDevice, categorize, ecodes
import select, time, subprocess, asyncio, logging
import paho.mqtt.client as mqtt
from systemd.journal import JournalHandler

# -----------------------------------
# CONFIGURE LOGGING TO SYSTEM JOURNAL
# -----------------------------------
logging.basicConfig()
logger = logging.getLogger('scrmgr.py')
logger.addHandler(JournalHandler())
logger.propagate = False
logger.setLevel(logging.INFO)
logger.info(" +++ scrmgr started")

# --------------
# CONFIGURE MQTT
# --------------
client = mqtt.Client()
broker_host = "localhost"
broker_port =  1883
# topics = [("pygpio/#",0)]

DIM_DELAY=5 
OFF_DELAY=600
SCR_STATE="OFF"

# ------------------------
# SCREEN CONTROL FUNCTIONS
# ------------------------
def screen_dim():
   global SCR_STATE
   if SCR_STATE != "DIM":
      SCR_STATE = "DIM"
      subprocess.run('sudo sh -c "echo 5 > /sys/class/backlight/10-0045/brightness"',shell=True)

def screen_off():
   global SCR_STATE
   if SCR_STATE != "OFF":
      SCR_STATE = "OFF"
      subprocess.run('sudo sh -c "echo 0 > /sys/class/backlight/10-0045/brightness"',shell=True)
#      publish_message("gpio/available","offline")

def screen_on():
   global SCR_STATE
   if SCR_STATE != "ON": 
      SCR_STATE="ON"
      subprocess.run('sudo sh -c "echo 31 > /sys/class/backlight/10-0045/brightness"',shell=True)
      time.sleep(0.1)
 #     publish_message("gpio/available","online")

# -------------------------
# PROCESS INCOMING MESSAGES
# -------------------------
def on_message(client, userdata, msg):
   logger.info(" +++ received topic=" + msg.topic + " payload=" + str(msg.payload))

# ----------------
# PUBLISH MESSAGES
# ----------------
def publish_message(topic, payload):
   client.publish(topic, payload,qos=0,retain=True)
   logger.info(" +++ published topic=" + topic + ", payload=" + str(payload))

# ----------------------------
# CALLBACK FOR MQTT CONNECTION
# ----------------------------
def on_connect(client, userdata, flags, rc):
   if rc == 0:
      logger.info(" +++ connected to mosquitto host")
#      publish_message("gpio/available","online")
#       client.subscribe(topics)
   else:
      logger.info(" +++ failed to connect with code %d\n", rc)

# -------------------------------
# CALLBACK FOR MQTT DISCONNECTION
# -------------------------------
def on_disconnect(client, userdata, rc):
   logger.info(" +++ disconnected from mosquitto host")

# ===========================================================================

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.connect(broker_host, broker_port, 60)
client.loop_start()

device = InputDevice('/dev/input/event4')
start = time.time()
last_event_time = start

while True:

   current_time = time.time()

   if (current_time - last_event_time) > OFF_DELAY:
      screen_off()
   elif current_time - last_event_time > DIM_DELAY:
      screen_dim()
   else:
      screen_on() 

   r, w, x = select.select([device], [], [], 0.1)

   if r:
      for event in device.read():
         print("nonce")
         last_event_time = time.time()
