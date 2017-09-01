#!/usr/bin/python3

# mqtt_server_client.py
# Copyright 2017 Lukas Friedrichsen
# License: Apache License Version 2.0
#
# 2017-06-01
#
# Description: This implementation of the Python paho-mqtt client allows to
# connect to a MQTT broker and log the data published on definable topics.
# Furthermore, it provides the functionality to act as an interface towards other,
# non-MQTT based applications like e.g. an OPC UA server by generating
# data-exchange-files, containing the most current values
# published on the subscribed topics at all times.

import paho.mqtt.client as mqtt
import time
import ssl
import sys
import os

#------------------------------#
########### Settings ###########
#------------------------------#

# General:

# System paths
_LOG='/var/log/mqtt_server_client/mqtt_server_client.log'
_DB='/var/lib/mqtt_server_client/mqtt_server_client.db.csv'
_EXCHANGE_DIR='/usr/local/var/'

_USER_CREDENTIALS='/usr/local/etc/mqtt_server_client/user_credentials'
_CA='/usr/local/share/ca-certificates/ca_cert.pem'

# MQTT:

# User credentials
with open(_USER_CREDENTIALS, 'r') as user_credentials:
    _USERNAME=user_credentials.readline().rstrip('\n')
    _PASSWORD=user_credentials.readline().rstrip('\n')

# Topics to subscribe to
_TOPICS='emra/+'

# CSV delimiter
_CSV_DELIMITER=','

# Local IP-address to bind the MQTT client to
_IP_ADDR_LOCAL='127.0.0.1'

# Remote IP-address of the MQTT broker
_IP_ADDR_REMOTE='192.168.42.1'

# Port of the MQTT broker
_MQTT_PORT=8883

# Timeout threshold (in s; maximum period allowed between communications with the
# broker (if no other messages are exchanged, this controls the rate at which the
# client pings the broker)
_MQTT_TIMEOUT=60

#------------------------------#
######## Implementation ########
#------------------------------#

class MQTT_Server_Client(object):
    '''
    This implementation of the Python paho-mqtt client allows to connect to a
    MQTT broker and log the data published on definable topics.

    Furthermore, it provides the functionality to act as an interface towards
    other, non-MQTT based applications like e.g. an OPC UA server by generating
    data-exchange-files, containing the most current values published on the
    subscribed topics at all times.
    '''

    # Initialization method, that is called on the creation of every new client
    # instance; initialize needed class variables and set the destination of the
    # log- and data-exchange-files
    def __init__(self, **kwargs):
        '''
        Initialization method, that is called on the creation of every new client
        instance; initialize needed class variables and set the destination of
        the log- and data-exchange-files

        Permitted transfer parameters:
        - log_file      (default: /var/log/mqtt_node_client/mqtt_node_client.log)
        - database      (default: /var/lib/mqtt_node_client/mqtt_node_client.db.csv)
        - exchange_dir  (default: /usr/local/var/)
        - delimiter     (default: ,)
        '''
        # Evaluate the transfer parameters
        self._log = kwargs.get('log_file', '/var/log/mqtt_node_client/mqtt_node_client.log')
        self._db = kwargs.get('database', '/var/lib/mqtt_node_client/mqtt_node_client.db.csv')
        self._exchange_dir = kwargs.get('exchange_dir', '/usr/local/var/')
        self._csv_delimiter = kwargs.get('csv_delimiter', ',')

        # Initialize _client
        self._client = None

    # General:

    # Get the current date and time and format the output
    # Format: yyyy-mm-dd hh:mm:ss
    def get_datetime(self):
        '''Get the current date and time and format the output'''
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

    # MQTT:

    # Callback function, which is called after an attempt to connect to the MQTT
    # broker; evaluate the connection result and, in case of a successfully
    # established connection, subscribe the defined topics (reconnection is
    # managed by the network loop in any other case)
    def _on_connect_cb(self, client_instance, userdata, flags, return_code):
        '''Callback function, which is called after an attempt to connect to the MQTT broker'''
        log_buffer=(self.get_datetime()+'_on_connect_cb: Return code: '+mqtt.connack_string(return_code)+'\n')

        # Connection attempt was successfull
        if return_code == mqtt.CONNACK_ACCEPTED:
            log_buffer+=(self.get_datetime()+'_on_connect_cb: Subscribing to the defined topics!\n')
            # Subscribe to the defined topics; retry every 30 seconds if the
            # subscription fails
            try:
                while (self._client.subscribe(topic=self._topics, qos=1)[0] != mqtt.MQTT_ERR_SUCCESS):
                    log_buffer+=(self.get_datetime()+'_on_connect_cb: Subscription failed! No connection to the broker! Retrying in 30 seconds!\n')
                    time.sleep(30)
                log_buffer+=(self.get_datetime()+'_on_connect_cb: Successfully subscribed to the defined topics!\n')
            except:
                log_buffer+=(self.get_datetime()+'_on_connect_cb: Error: '+str(sys.exc_info()[1])+'\n')
        # Connection attempt wasn't successfull
        else:
            log_buffer+=(self.get_datetime()+'_on_connect_cb: Trying again!\n')

        # Write the buffer to the log (the usage of a buffer allows to minimalize
        # file is opened (and therewith occupied) by the program, thus reducing
        # the risk of an access conflict)
        with open(self._log, 'a') as log:
            log.write(log_buffer)

    # Callback function, which is called after the client disconnected the MQTT
    # broker; evaluate the connection result and, in case of an intended
    # disconnect, exit the program (reconnection is managed by the network loop
    # in any other case)
    def _on_disconnect_cb(self, client_instance, userdata, return_code):
        '''Callback function, which is called after the client disconnected the MQTT broker'''
        log_buffer=(self.get_datetime()+' _on_disconnect_cb: Disconnected from the broker! Return code: '+mqtt.error_string(return_code)+'\n')

        # Exit the program if the disconnect was caused by client.disconnect()
        if return_code == mqtt.MQTT_ERR_SUCCESS:
            log_buffer+=(self.get_datetime()+' _on_disconnect_cb: Exiting the program!\n')

            # Exit the program
            sys.exit()
        else:
            log_buffer+=(self.get_datetime()+' _on_disconnect_cb: Trying to reconnect!\n')

        # Write the buffer to the log (the usage of a buffer allows to minimalize
        # file is opened (and therewith occupied) by the program, thus reducing
        # the risk of an access conflict)
        with open(self._log, 'a') as log:
            log.write(log_buffer)

    # Callback function, that is called everytime a new message is published on
    # a topic subscribed by the client; log the message received and write it to
    # the data-exchange-file
    def _on_message_cb(self, client_instance, userdata, msg):
        '''Callback function, that is called everytime a new message is published on a topic subscribed by the client'''
        log_buffer=(self.get_datetime()+'_on_message_cb: Obtained message '+str(msg.payload).lstrip('b').strip("'")+' on topic '+msg.topic+'\n')

        # Write the message received to the database
        with open(self._db, 'a') as database:
            database.write(self.get_datetime()+self._csv_delimiter+msg.topic[msg.topic.rfind('/')+1:]+self._csv_delimiter+str(msg.payload).lstrip('b').strip("'")+'\n')

        try:
            # Create the respective sub-directories in the data-exchange-directory
            # if they don't exist yet
            _exchange_file=self._exchange_dir+msg.topic
            os.makedirs(_exchange_file[:_exchange_file.rfind('/')], exist_ok=True)

            # Generate a temporary file containing the data received
            with open(_exchange_file+'.temp', 'w') as data_exchange_file:
                data_exchange_file.write(str(msg.payload).lstrip('b').strip("'"))
                data_exchange_file.flush()
                os.fsync(data_exchange_file.fileno())
        except FileNotFoundError:
            # Every then and now, the system cleans up the data-exchange-directory
            # and removes outdate files and empty directories. If this garbage
            # collector checks on a directory just between os.makedirs(...) and
            # open(...), it will only see an empty directory and remove it (a
            # wild runtime-condition occurs). The result is a FileNotFoundError.
            # In this case, the message received can still be found in the
            # database, but the respective data-exchange-file isn't created.
            log_buffer+=(self.get_datetime()+'_on_message_cb: Error! No such file or directory: '+_exchange_file+'\n')
        except:
            log_buffer+=(self.get_datetime()+'_on_message_cb: Error: '+str(sys.exc_info()[1])+'\n')

        # Replace the current data-exchange-file with the temporary file
        #
        # The OPC UA-server constantly tries to read the content from the data-
        # exchange-file. So, to avoid complications arising from a simultaneous
        # access to the resource, the file has to be edited in an atomic manner
        # ("to make the object thread-safe").
        # The only real way to achieve this is to write the message to a second
        # file and replace the original data-exchange-file by it in one step (by
        # editing the object's inode). This is done via the os.rename(...) command.
        # According to https://docs.python.org/3/library/os.html:
        #
        #       "If successful, the renaming will be an atomic operation (this is
        #       a POSIX requirement)."
        try:
            os.rename(_exchange_file+'.temp', _exchange_file)
        except:
            log_buffer+=(self.get_datetime()+'_on_message_cb: Error: '+str(sys.exc_info()[1])+'\n')

        # Write the buffer to the log (the usage of a buffer allows to minimalize
        # file is opened (and therewith occupied) by the program, thus reducing
        # the risk of an access conflict)
        with open(self._log, 'a') as log:
            log.write(log_buffer)

    # Initialize and configure the MQTT client
    def mqtt_node_client_init(self, remote_ip, port, topics, local_ip, username, password, **kwargs):
        '''
        Initialize and configure the MQTT client

        Permitted transfer parameters:
        - client_id (default: value of username)
        - ca        (default: None)
        - timeout   (default: 60)
        '''
        # Evaluate the transfer parameters
        cl_id = kwargs.get('client_id', username)
        ca = kwargs.get('ca', None)
        timeout = kwargs.get('timeout', 60)

        self._topics = topics

        with open(self._log, 'a') as log:
            log.write(
                self.get_datetime()+' mqtt_node_client_init: Initializing and configuring the MQTT client!\n'+
                self.get_datetime()+' mqtt_node_client_init: Local IP: '+local_ip+'   Remote IP: '+remote_ip+'   Port: '+str(port)+'\n'
            )

        try:
            # Initialize the MQTT client and set the respective callback functions
            self._client = mqtt.Client(client_id=cl_id, clean_session=False, userdata=None, protocol=mqtt.MQTTv31, transport='tcp')
            self._client.on_connect = self._on_connect_cb
            self._client.on_disconnect = self._on_disconnect_cb
            self._client.on_message = self._on_message_cb

            if ca != None:
                # Configure the encryption related settings like which TLS version
                # to use when communicating with the broker or where to find the
                # corresponding CA-certificate
                self._client.tls_set(ca_certs=ca, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)

            # Set username and password
            self._client.username_pw_set(username=username, password=password)

            # Try to connect to the broker in a non-blocking way and start a
            # loop to keep the connection alive afterwards. This network loop also
            # automatically handles the reconnection to the broker in case the
            # connection is lost without explicitly calling client.disconnect().
            self._client.connect_async(host=remote_ip, port=port, keepalive=timeout, bind_address=local_ip)
            self._client.loop_forever(retry_first_connection=True)
        except:
            # Log occuring errors
            with open(self._log, 'a') as log:
                log.write(self.get_datetime()+' mqtt_node_client_init: Error: '+str(sys.exc_info()[1])+'\n')

            # Check, if the MQTT client has already been initialized
            if self._client != None:
                # Disconnect from the MQTT broker
                self._client.disconnect()
            else:
                # Exit the program directly (instead of from _on_disconnect_cb(...))
                sys.exit()

#------------------------------#
######### Main program #########
#------------------------------#

# Create a new instance of MQTT_Node_Client
client = MQTT_Server_Client(log_file=_LOG, database=_DB, exchange_dir=_EXCHANGE_DIR, csv_delimiter=_CSV_DELIMITER)

# Initialize the MQTT-client
client.mqtt_node_client_init(remote_ip=_IP_ADDR_REMOTE, port=_MQTT_PORT, topics=_TOPICS, local_ip=_IP_ADDR_LOCAL, username=_USERNAME, password=_PASSWORD, ca=_CA, timeout=_MQTT_TIMEOUT)
