#!/bin/bash
sudo mosquitto_sub -d --cafile ~/ca_cert.pem -h 192.168.42.1 -p 8883 -i test -k 5 -u testDevice -P mqtt_testDevice -t '$SYS/broker/uptime' -q 0
