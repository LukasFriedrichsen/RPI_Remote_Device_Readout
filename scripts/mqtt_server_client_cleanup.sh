#!/bin/bash
# Paths
LOG_PATH=/var/log/mqtt_server_client/mqtt_server_client.log
DB_PATH=/var/lib/mqtt_server_client/mqtt_server_client.db.csv
EX_PATH=/usr/local/var

# Lines to keep
LOG_LINES=17280
DB_LINES=17280

# Delete all lines but the last LOG_LINES from mqtt_server_client.log
tail -n $LOG_LINES $LOG_PATH > $LOG_PATH.temp
mv $LOG_PATH.temp $LOG_PATH

# Delete all lines but the last DB_LINES from mqtt_server_client.db
tail -n $DB_LINES $DB_PATH.temp > $DB_PATH.temp
mv $DB_PATH.temp $DB_PATH

# Clean up the data-exchange-directory (delete all files that weren't
# modified in the last 30 days as well as empty sub-directories)
find $EX_PATH -mtime +30 -delete
find $EX_PATH -type d -empty -delete
