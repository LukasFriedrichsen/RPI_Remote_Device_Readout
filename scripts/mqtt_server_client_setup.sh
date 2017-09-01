#!/bin/bash
# Paths
CA_CPY_PATH=/usr/local/share/ca-certificates/ca_cert.pem
CA_ORIGINAL_PATH=/etc/mosquitto/ca_certificates/ca_cert.pem
LOG_PATH=/var/log/mqtt_server_client
DB_PATH=/var/lib/mqtt_server_client
EXCHANGE_PATH=/usr/local/var
USR_CRED_PATH=/usr/local/etc/mqtt_server_client

# Create a symbolic link to the CA-certificate used to sign the MQTT broker's
# server certificate
sudo cp -f -s $CA_ORIGINAL_PATH $CA_CPY_PATH

# Create the directory for the log file
sudo mkdir -p $LOG_PATH

# Create the directory for the database
sudo mkdir -p $DB_PATH

# Create the directory for the data-exchange-files
sudo mkdir -p $EXCHANGE_PATH

# Create the file containing the user credentials
sudo mkdir -p $USR_CRED_PATH
sudo touch $USR_CRED_PATH/user_credentials
sudo sed -e 's/^.*&&& //' > $USR_CRED_PATH/user_credentials << EndUserCredentials
	&&& username
	&&& password
EndUserCredentials
sudo chmod 600 $USR_CRED_PATH/user_credentials
