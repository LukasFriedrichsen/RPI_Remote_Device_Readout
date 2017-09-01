#!/bin/bash
# Paths
LOG_PATH=/var/log/mqtt_node_client
DB_PATH=/var/lib/mqtt_node_client
USR_CRED_PATH=/usr/local/etc/mqtt_node_client

# Create the directory for the log file
sudo mkdir -p $LOG_PATH

# Create the directory for the database
sudo mkdir -p $DB_PATH

# Create the file containing the user credentials
sudo mkdir -p $USR_CRED_PATH
sudo touch $USR_CRED_PATH/user_credentials.py
sudo sed -e 's/^.*&&& //' > $USR_CRED_PATH/user_credentials << EndUserCredentials
	&&& username
	&&& password
EndUserCredentials
sudo chmod 600 $USR_CRED_PATH/user_credentials
