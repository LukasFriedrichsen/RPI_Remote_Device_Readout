#!/bin/bash
# Paths
LOG_PATH=/var/log/mqtt_node_client/mqtt_node_client.log
DB_PATH=/var/lib/mqtt_node_client/mqtt_node_client.db.csv

# Lines to keep
LOG_LINES=1728
DB_LINES=1728

# Delete all lines but the last LOG_LINES from mqtt_node_client.log
tail -n $LOG_LINES $LOG_PATH > $LOG_PATH.temp
mv $LOG_PATH.temp $LOG_PATH

# Delete all lines but the last DB_LINES from mqtt_node_client.db
tail -n $DB_LINES $DB_PATH.temp > $DB_PATH.temp
mv $DB_PATH.temp $DB_PATH
