#!/bin/bash
# Subject
SUBJ_BASE="/O=KRONPRINZ GmbH/OU=Innovation Management/emailAddress=lukas.friedrichsen@kronprinz.de"
SUBJ_CA="/CN=EMRA_MQTT_CA_certificate$SUBJ_BASE"
SUBJ_SERVER="/CN=EMRA_MQTT_server_certificate$SUBJ_BASE"

# Generate a temporary file to store the x509_v3 extensions for the server-certificate in since they can't be passed directly via the command line
EXT_TEMP=$(mktemp /tmp/ext_temp.XXX) || { echo "Can't create temporary file!"; exit 1; }
sed -e 's/^.*&&& //' > $EXT_TEMP << EndExtensions
	&&& [ Extensions ]
	&&& basicConstraints=critical,CA:false
	&&& keyUsage=keyEncipherment
  &&& extendedKeyUsage=serverAuth
	&&& subjectAltName=IP:192.168.42.1,IP:127.0.0.1
EndExtensions

# Remove possible old certificates
echo "Removing possible old certificates!"
sudo rm -f /etc/mosquitto/ca_certificates/ca_*
sudo rm -f /etc/mosquitto/certs/server_*

# CA-certificate
echo "Generating CA-certificate!"
sudo openssl req -x509 -sha256 -newkey rsa:2048 -nodes -keyout /etc/mosquitto/ca_certificates/ca_key.pem -days 3652 -extensions v3_ca -subj "$SUBJ_CA" -out /etc/mosquitto/ca_certificates/ca_cert.pem
sudo chmod 400 /etc/mosquitto/ca_certificates/ca_key.pem
sudo chmod 444 /etc/mosquitto/ca_certificates/ca_cert.pem

# Server-certificate CSR
echo "Generating server-certificate CSR!"
sudo openssl req -sha256 -newkey rsa:2048 -nodes -keyout /etc/mosquitto/certs/server_key.pem -extensions v3_ca -subj "$SUBJ_SERVER" -out /etc/mosquitto/certs/server_cert.csr
sudo chmod 400 /etc/mosquitto/certs/server_key.pem
sudo chown mosquitto /etc/mosquitto/certs/server_key.pem

# Sign server-certificate CSR
echo "Signing server-certificate CSR with the generated CA-certificate!"
sudo openssl x509 -req -in /etc/mosquitto/certs/server_cert.csr -CA /etc/mosquitto/ca_certificates/ca_cert.pem -CAkey /etc/mosquitto/ca_certificates/ca_key.pem -CAcreateserial -days 3652 -extfile $EXT_TEMP -extensions Extensions -out /etc/mosquitto/certs/server_cert.pem
sudo chmod 444 /etc/mosquitto/certs/server_cert.pem
sudo chown mosquitto /etc/mosquitto/certs/server_cert.pem

# Clean up
sudo rm -f /etc/mosquitto/certs/server_cert.csr
rm $EXT_TEMP
