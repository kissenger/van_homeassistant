from evdev import InputDevice, categorize, ecodes
import select, time, subprocess, asyncio

DIM_DELAY=30
OFF_DELAY=600
SCR_STATE="OFF"

device = InputDevice('/dev/input/event4')
start = time.time()
last_event_time = start

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

def screen_on():
   global SCR_STATE
   if SCR_STATE != "ON": 
      SCR_STATE="ON"
      subprocess.run('sudo sh -c "echo 31 > /sys/class/backlight/10-0045/brightness"',shell=True)

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
         last_event_time = time.time()
