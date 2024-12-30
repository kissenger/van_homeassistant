#!/bin/bash
sudo docker compose down
sudo docker rm -f $(sudo docker ps -a -q)
sudo docker image remove -f $(sudo docker images -a -q)
sudo rm ~/proj/mosquitto/data/mosquitto.db
