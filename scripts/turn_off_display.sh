#!/bin/bash
sed -i '/dpms_timeout=/c\dpms_timeout=1' ~/.config/wayfire.ini
sleep 1
sed -i '/dpms_timeout=/c\dpms_timeout=30' ~/.config/wayfire.ini
