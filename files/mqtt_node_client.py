#!/usr/bin/python3

# mqtt_node_client.py
# Copyright 2017 Lukas Friedrichsen
# License: Apache License Version 2.0
#
# 2017-06-19
#
# Description: This combined implementation of the Python paho-mqtt client,
# pymodbus and python-mbus provides the functionality to read out connected
# Modbus RTU resp. M-Bus devices and to communicate the values received over the
# network, e.g. to a central processing unit via MQTT.
#
# This class can either be used as an offline, standalone data logger, in which
# the values received from the connected devices are only written to a local
# database in the CSV format, or it can serve as an online MQTT client, where the
# values are furthermore automatically communicated to a user definable broker,
# thus creating a gateway between the chosen bus protocol and any other MQTT
# capable device.

import paho.mqtt.client as mqtt
import pymodbus.client.sync as modbus
import mbus.MBus as mbus
import time
import ssl
import sys
import os

#------------------------------#
########### Settings ###########
#------------------------------#

# General:

# System paths
_LOG='/var/log/mqtt_node_client/mqtt_node_client.log'
_DB='/var/lib/mqtt_node_client/mqtt_node_client.db.csv'

_USER_CREDENTIALS='/usr/local/etc/mqtt_node_client/user_credentials'
_CA='/usr/local/share/ca-certificates/ca_cert.pem'

_LIBMBUS_SO='/usr/local/lib/libmbus.so'

# MQTT:

# User credentials
with open(_USER_CREDENTIALS, 'r') as user_credentials:
    _USERNAME=user_credentials.readline().rstrip('\n')
    _PASSWORD=user_credentials.readline().rstrip('\n')

# Topic to publish to
_TOPIC='emra/'+_USERNAME

# CSV delimiter
_CSV_DELIMITER=','

# Local IP-address to bind the MQTT client to
with os.popen('ifconfig wlan0 | grep "inet\ addr" | cut -d: -f2 | cut -d" " -f1', 'r') as ip_addr_local:
    _IP_ADDR_LOCAL=ip_addr_local.read()

# Remote IP-address of the MQTT broker
_IP_ADDR_REMOTE='192.168.42.1'

# Port of the MQTT broker
_MQTT_PORT=8883

# Timeout threshold (in s; maximum period allowed between communications with the
# broker (if no other messages are exchanged, this controls the rate at which the
# client pings the broker)
_MQTT_TIMEOUT=60

# Modbus RTU/M-Bus (general):

# Operation mode; determines which bus-protocol is chosen
# 0 - Modbus RTU
# 1 - M-Bus
_OP_MODE=0

# Port which the Modbus RTU resp. M-Bus devices are connected to
_BUS_PORT='/dev/ttyUSB0'

# Baud rate to use
_BAUDRATE=9600

# Address of the Modbus RTU resp. M-Bus device to read from
_BUS_ADDRESS=1

# Time-interval between the readout procedures (in s)
_READ_INTERVAL=5

# Modbus RTU:

# (Start-)Register to read out (Modbus specific)
_MODBUS_REGISTER=50536

# Number of registers to read out starting from _MODBUS_REGISTER
# One register is of 16 bits length, so to e.g. read out a 32 bit long variable,
# _MODBUS_REGISTER_COUNT has to be set to 2 and so on.
_MODBUS_REGISTER_COUNT=2

# Signed
# 0 - Unsigned
# 1 - Signed
_MODBUS_SIGNED=0

# Endianness
# 0 - Big Endian
# 1 - Little Endian
_MODBUS_ENDIANNESS=0

# Bit significance
# 0 - MSB
# 1 - LSB
_MODBUS_BIT_SIGNIFICANCE=0

# Number of stop bits
_MODBUS_STOPBITS=1

# Bytesize of the message frames in bits
_MODBUS_BYTESIZE=8

# Parity
# E - Even
# O - Odd
# N - None
_MODBUS_PARITY='N'

# Timeout threshold (in s; if no answer to a request is obtained within the defined
# period of time, the master asserts that the slave timed out and raises an error)
_MODBUS_TIMEOUT=3

#------------------------------#
######## Implementation ########
#------------------------------#

class MQTT_Node_Client(object):
    '''
    This combined implementation of the Python paho-mqtt client, pymodbus and
    python-mbus provides the functionality to read out connected Modbus RTU resp.
    M-Bus devices and to communicate the values received over the network, e.g.
    to a central processing unit via MQTT.

    This class can either be used as an offline, standalone data logger, in which
    case the values received from the connected devices are only written to a
    local database in the CSV format, or it can serve as an online MQTT client,
    where the values are furthermore automatically communicated to a user
    definable broker, thus creating a gateway between the chosen bus protocol and
    any other MQTT capable device.
    '''

    # Initialization method, that is called on the creation of every new client
    # instance; set the location of the log-files as well as the start time of
    # the process, initialize needed class variables and create the references
    # between the externally usable API elements and the corresponding internal
    # functions
    def __init__(self, op_mode, **kwargs):
        '''
        Initialization method, that is called on the creation of every new client
        instance; set the location of the log-files as well as the start time of
        the process, initialize needed class variables and create the references
        between the externally usable API elements and the corresponding internal
        functions

        Permitted transfer parameters:
        - log_file      (default: /var/log/mqtt_node_client/mqtt_node_client.log)
        - database      (default: /var/lib/mqtt_node_client/mqtt_node_client.db.csv)
        - delimiter     (default: ,)
        '''
        # Evaluate the transfer parameters
        self._log = kwargs.get('log_file', '/var/log/mqtt_node_client/mqtt_node_client.log')
        self._db = kwargs.get('database', '/var/lib/mqtt_node_client/mqtt_node_client.db.csv')
        self._csv_delimiter = kwargs.get('csv_delimiter', ',')

        # Set the start time and initialize _client and _bus_master
        self._startTime = time.time()
        self._client = None
        self._bus_master = None

        try:
            # Create the references between the externally usable API elements
            # and the corresponging internal functions depending on the chosen
            # operation mode, thus covering up internal complexity and
            # simplifying the usage of the class, whilst making sure, that only
            # one bus master is activ at the same time (cf. facade pattern
            # (software design pattern))
            # 0 - Modbus RTU
            # 1 - M-Bus
            if (op_mode == 0):
                # Set bus_init to _modbus_rtu_init
                self.bus_init = self._modbus_rtu_init
            elif (op_mode == 1):
                # Set bus_init to _mbus_init
                self.bus_init = self._mbus_init
            else:
                # Invalid operation mode
                raise Exception('Invalid operation mode!')
        except:
            # Log occuring errors
            with open(self._log, 'a') as log:
                log.write(self.get_uptime()+' __init__: Error: '+str(sys.exc_info()[1])+'\n')

            # Exit the program
            sys.exit()

    # General:

    # Get the uptime of the process and format the output
    def get_uptime(self):
        '''Get the uptime of the process and format the output'''
        return str(int(time.time()-self._startTime))

    # MQTT:

    # Callback function, which is called after an attempt to connect to the MQTT
    # broker and which evaluates the connection result (reconnection is managed
    # by the loop thread)
    def _on_connect_cb(self, client_instance, userdata, flags, return_code):
        '''Callback function, which is called after an attempt to connect to the MQTT broker'''
        log_buffer=(self.get_uptime()+' _on_connect_cb: Return code: '+mqtt.connack_string(return_code)+'\n')

        # Connection attempt was successfull
        if return_code == mqtt.CONNACK_ACCEPTED:
            log_buffer+=(self.get_uptime()+' _on_connect_cb: Subscribing to the defined topics!\n')
        # Connection attempt wasn't successfull
        else:
            log_buffer+=(self.get_uptime()+' _on_connect_cb: Trying again!\n')

        # Write the buffer to the log (the usage of a buffer allows to minimalize
        # file is opened (and therewith occupied) by the program, thus reducing
        # the risk of an access conflict)
        with open(self._log, 'a') as log:
            log.write(log_buffer)

    # Callback function, which is called after the client disconnected the MQTT
    # broker; evaluate the connection result and, in case of an intended disconnect,
    # exit the program (reconnection is managed by the loop thread in any other
    # case)
    def _on_disconnect_cb(self, client_instance, userdata, return_code):
        '''Callback function, which is called after the client disconnected the MQTT broker'''
        log_buffer=(self.get_uptime()+' _on_disconnect_cb: Disconnected from the broker! Return code: '+mqtt.error_string(return_code)+'\n')

        # Exit the program if the disconnect was caused by client.disconnect()
        if return_code == mqtt.MQTT_ERR_SUCCESS:
            log_buffer+=(self.get_uptime()+' _on_disconnect_cb: Stopping the loop thread and exiting the program!\n')

            # Stop the MQTT client thread
            self._client.loop_stop()

            # Exit the program
            sys.exit()
        else:
            log_buffer+=(self.get_uptime()+' _on_disconnect_cb: Trying to reconnect!\n')

        # Write the buffer to the log (the usage of a buffer allows to minimalize
        # file is opened (and therewith occupied) by the program, thus reducing
        # the risk of an access conflict)
        with open(self._log, 'a') as log:
            log.write(log_buffer)

    # Callback function, that is called everytime a new message is published by
    # the client; log the message sent and write it to the data-exchange-file
    def _on_publish_cb(self, client_instance, userdata, mid):
        '''Callback function, that is called everytime a new message is published by the client'''
        # Write the message sent to the log file
        with open(self._log, 'a') as log:
            log.write(self.get_uptime()+' _on_publish_cb: Published message '+str(userdata)+' on topic '+self._topic+'\n')

    # Publish the message given as transfer parameter
    def mqtt_publish(self, msg):
        '''Publish the message given as transfer parameter'''

        # Check, if the MQTT client has already been initialized
        if self._client != None:
            try:
                if (msg == None):
                    raise Exception('Invalid transfer parameter!')

                # Set msg as transfer parameter for the on-publish callback-
                # function
                self._client.user_data_set(msg)
                # Publish the message
                self._client.publish(topic=self._topic, payload=msg, qos=1)
            except:
                # Log occuring errors
                with open(self._log, 'a') as log:
                    log.write(self.get_uptime()+' mqtt_publish: Error: '+str(sys.exc_info()[1])+'\n')


    # Initialize and configure the MQTT client
    def mqtt_node_client_init(self, remote_ip, port, topic, local_ip, username, password, **kwargs):
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

        self._topic = topic

        with open(self._log, 'a') as log:
            log.write(
                self.get_uptime()+' mqtt_node_client_init: Initializing and configuring the MQTT client!\n'+
                self.get_uptime()+' mqtt_node_client_init: Local IP: '+local_ip+'   Remote IP: '+remote_ip+'   Port: '+str(port)+'\n'
            )

        try:
            # Initialize the MQTT client and set the respective callback functions
            self._client = mqtt.Client(client_id=cl_id, clean_session=False, userdata=None, protocol=mqtt.MQTTv31, transport='tcp')
            self._client.on_connect = self._on_connect_cb
            self._client.on_disconnect = self._on_disconnect_cb
            self._client.on_publish = self._on_publish_cb

            # Set a will to be sent to the MQTT broker. If the client disconnects
            # without calling disconnect(), the broker will publish the message
            # on its behalf.
            self._client.will_set(topic=self._topic, payload='Node disconnected!', qos=0)

            if ca != None:
                # Configure the encryption related settings like which TLS version
                # to use when communicating with the broker or where to find the
                # corresponding CA-certificate
                self._client.tls_set(ca_certs=ca, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)

            # Set username and password
            self._client.username_pw_set(username=username, password=password)

            # Try to connect to the broker in a non-blocking way and start a
            # thread to keep the connection alive afterwards. This thread also
            # automatically handles the reconnection to the broker in case the
            # connection is lost without explicitly calling client.disconnect().
            self._client.connect_async(host=remote_ip, port=port, keepalive=timeout, bind_address=local_ip)
            self._client.loop_start()
        except:
            # Log occuring errors
            with open(self._log, 'a') as log:
                log.write(self.get_uptime()+' mqtt_node_client_init: Error: '+str(sys.exc_info()[1])+'\n')

            # Check, if the MQTT client has already been initialized
            if self._client != None:
                # Disconnect from the MQTT broker
                self._client.disconnect()
            else:
                # Exit the program directly (instead of from _on_disconnect_cb(...))
                sys.exit()

    # Modbus RTU:

    # Periodical readout of the defined Modbus RTU device
    def _modbus_rtu_loop(self):
        '''Start the periodical readout of the defined Modbus RTU device'''
        with open(self._log, 'a') as log:
            log.write(self.get_uptime()+' _modbus_rtu_loop: Starting periodical readout of the defined Modbus RTU device!\n')

        try:
            while (True):
                # Read _MODBUS_REGISTER_COUNT registers starting from
                # _MODBUS_REGISTER from device _BUS_ADDRESS
                data_raw = self._bus_master.read_holding_registers(unit=self._address, address=self._modbus_register, count=self._modbus_register_count)

                # Check, if the read operation was successfull and try again if not
                if (not data_raw):
                    # Check, if the MQTT client has already been initialized
                    if self._client != None:
                        self.mqtt_publish('No device connected at address '+str(self._address)+'\n')

                    # Sleep for self._read_interval seconds
                    time.sleep(self._read_interval)

                    continue

                # Change the byte order to little endian
                if (not self._modbus_endianness):
                    # Change the order of the registers
                    data_raw.registers = data_raw.registers[::-1]
                    # Change the order of the bytes within the single registers
                    for idx in range(len(data_raw.registers)):
                        data_raw.registers[idx] = int(bin(data_raw.registers[idx])[10:]+bin(data_raw.registers[idx])[2:10], 2)

                # Change the bit significance to MSB
                if (self._modbus_bit_significance):
                    for idx in range(len(data_raw.registers)):
                        data_raw.registers[idx] = int(bin(data_raw.registers[idx])[:1:-1] ,2)

                # Calculate the actual (combined) value of the registers read
                data = 0
                for idx in range(len(data_raw.registers)):
                    data+=data_raw.registers[idx]<<((len(data_raw.registers)-idx-1)*16)

                # Evaluate the signing
                if (self._modbus_signed):
                    if (bin(data)[2]):
                        data = -((data-1)^int('FFFF'*self._modbus_register_count, 16))

                # Write the message read to the log file
                with open(self._log, 'a') as log:
                    log.write(self.get_uptime()+' _mbus_loop: Data read from device '+str(self._address)+': '+str(data)+'\n')

                # Write the message read to the database
                with open(self._db, 'a') as database:
                    database.write(self.get_uptime()+self._csv_delimiter+self._topic[self._topic.rfind('/')+1:]+self._csv_delimiter+str(data)+'\n')

                # Check, if the MQTT client has already been initialized
                if self._client != None:
                    # Publish the data received from the device
                    self.mqtt_publish(data)

                # Sleep for self._read_interval seconds
                time.sleep(self._read_interval)
        except:
            # Log occuring errors
            with open(self._log, 'a') as log:
                log.write(self.get_uptime()+' _modbus_rtu_loop: Error: '+str(sys.exc_info()[1])+'\n')

            # Check, if the Modbus RTU master has already been initialized
            if self._bus_master != None:
                # Disconnect from the bus and free all occupied resources
                self._bus_master.close()

            # Check, if the MQTT client has already been initialized
            if self._client != None:
                # Disconnect from the MQTT broker
                self._client.disconnect()
            else:
                # Exit the program directly (instead of from _on_disconnect_cb(...))
                sys.exit()

    # Initialize the Modbus RTU master and start it
    def _modbus_rtu_init(self, address, register, register_count, **kwargs):
        '''
        Initialize the Modbus RTU master and start it

        Permitted transfer parameters:
        - port              (default: /dev/ttyUSB0)
        - baudrate          (default: 9600)
        - read_interval     (default: 5)
        - timeout           (default: 3)
        - stopbits          (default: 1)
        - bytesize          (default: 8)
        - parity            (default: N)
        - signed            (default: 0)
        - endianness        (default: 0)
        - bit_significance  (default: 0)
        '''
        # Evaluate the transfer parameters
        serial_port = kwargs.get('port', '/dev/ttyUSB0')
        baud = kwargs.get('baudrate', 9600)
        modbus_timeout = kwargs.get('timeout', 3)
        modbus_stopbits = kwargs.get('stopbits', 1)
        modbus_byte_size = kwargs.get('bytesize', 8)
        modbus_parity = kwargs.get('parity', 'N')
        self._read_interval = kwargs.get('read_interval', 5)
        self._modbus_signed = kwargs.get('signed', 0)
        self._modbus_endianness = kwargs.get('endianness', 0)
        self._modbus_bit_significance = kwargs.get('bit_significance', 0)

        self._address = address
        self._modbus_register = register
        self._modbus_register_count = register_count

        with open(self._log, 'a') as log:
            log.write(
                self.get_uptime()+' _modbus_rtu_init: Initializing the Modbus RTU master and starting it!\n'+
                self.get_uptime()+' _modbus_rtu_init: Port: '+str(serial_port)+'\n'
            )

        try:
            # Initialize the Modbus RTU master
            self._bus_master = modbus.ModbusSerialClient(method='rtu', port=serial_port, baudrate=baud, timeout=modbus_timeout, stopbits=modbus_stopbits, bytesize=modbus_byte_size, parity=modbus_parity)

            # Connect the Modbus RTU master to the bus
            self._bus_master.connect()

            # Start the periodical readout of the defined Modbus RTU device
            self._modbus_rtu_loop()
        except:
            # Log occuring errors
            with open(self._log, 'a') as log:
                log.write(self.get_uptime()+' _modbus_rtu_init: Error: '+str(sys.exc_info()[1])+'\n')

            # Check, if the Modbus RTU master has already been initialized
            if self._bus_master != None:
                # Disconnect from the bus and free all occupied resources
                self._bus_master.close()

            # Check, if the MQTT client has already been initialized
            if self._client != None:
                # Disconnect from the MQTT broker
                self._client.disconnect()
            else:
                # Exit the program directly (instead of from _on_disconnect_cb(...))
                sys.exit()

    # M-Bus:

    # Periodical readout of the defined M-Bus device
    def _mbus_loop(self):
        '''Start the periodical readout of the defined M-Bus device'''
        with open(self._log, 'a') as log:
            log.write(self.get_uptime()+' _mbus_loop: Starting periodical readout of the defined M-Bus device!\n')

        try:
            while (True):
                # Send a request frame to the device with address addr
                self._bus_master.send_request_frame(address=self._address)

                # Wait for an answer from the slave device and try again, if the
                # read operation wasn't successfull
                data_raw = mbus.MBusFrame()
                if (self._bus_master._libmbus.recv_frame(self._bus_master.handle, data_raw) < 0):
                    # Check, if the MQTT client has already been initialized
                    if self._client != None:
                        self.mqtt_publish('No device connected at address '+str(self._address)+'\n')

                    # Sleep for self._read_interval seconds
                    time.sleep(self._read_interval)

                    continue

                # Extract the actual data from the message received
                data = self._bus_master.frame_data_parse(data_raw)

                # Write the message read to the log file
                with open(self._log, 'a') as log:
                    log.write(self.get_uptime()+' _mbus_loop: Data read from device '+str(_BUS_ADDRESS)+': '+str(data)+'\n')

                # Write the message read to the database
                with open(self._db, 'a') as database:
                        database.write(self.get_uptime()+self._csv_delimiter+self._topic[self._topic.rfind('/')+1:]+self._csv_delimiter+userdata+'\n')

                # Check, if the MQTT client has already been initialized
                if self._client != None:
                    # Publish the data received from the device
                    self.mqtt_publish(data)

                # Free the occupied resources (has to be done since the underlying
                # c-program mallocs the storage space for the variables)
                self._bus_master.frame_data_free(data)

                # Sleep for self._read_interval seconds
                time.sleep(self._read_interval)
        except:
            # Log occuring errors
            with open(self._log, 'a') as log:
                log.write(self.get_uptime()+' _mbus_loop: Error: '+str(sys.exc_info()[1])+'\n')

            # Check, if the MBus master has already been initialized
            if self._bus_master != None:
                # Disconnect from the bus and free all occupied resources
                self._bus_master.disconnect()

            # Check, if the MQTT client has already been initialized
            if self._client != None:
                # Disconnect from the MQTT broker
                self._client.disconnect()
            else:
                # Exit the program directly (instead of from _on_disconnect_cb(...))
                sys.exit()

    # Initialize the M-Bus master and start it
    def _mbus_init(self, address, **kwargs):
        '''
        Initialize the M-Bus master and start it

        Permitted transfer parameters:
        - port          (default: /dev/ttyUSB0)
        - baudrate      (default: 9600)
        - read_interval (default: 5)
        '''
        # Evaluate the transfer parameters
        serial_port = kwargs.get('port', '/dev/ttyUSB0')
        baud = kwargs.get('baudrate', 9600)
        self._read_interval = kwargs.get('read_interval', 5)

        self._address = address

        with open(self._log, 'a') as log:
            log.write(
                self.get_uptime()+' _mbus_init: Initializing the M-Bus master and starting it!\n'+
                self.get_uptime()+' _mbus_init: Port: '+str(serial_port)+'\n'
            )

        try:
            # Initialize the M-Bus master
            self._bus_master = mbus.MBus(device=serial_port, libpath=_LIBMBUS_SO)

            # Connect the M-Bus master to the bus
            self._bus_master.connect()

            # Set the baud rate to use
            if (self._bus_master._libmbus.serial_set_baudrate(self._bus_master.handle, baud) == -1):
                raise Exception('Failed to set the baudrate!')

            # Start the periodical readout of the defined M-Bus device
            self._mbus_loop()
        except:
            # Log occuring errors
            with open(self._log, 'a') as log:
                log.write(self.get_uptime()+' _mbus_init: Error: '+str(sys.exc_info()[1])+'\n')

            # Check, if the MBus master has already been initialized
            if self._bus_master != None:
                # Disconnect from the bus and free all occupied resources
                self._bus_master.disconnect()

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
client = MQTT_Node_Client(op_mode=_OP_MODE, log_file=_LOG, database=_DB, csv_delimiter=_CSV_DELIMITER)

# Initialize the MQTT-client
client.mqtt_node_client_init(remote_ip=_IP_ADDR_REMOTE, port=_MQTT_PORT, topic=_TOPIC, local_ip=_IP_ADDR_LOCAL, username=_USERNAME, password=_PASSWORD, ca=_CA, timeout=_MQTT_TIMEOUT)

# Initialize the Modbus RTU resp. M-Bus master depending on the operation mode
# and start the periodical readout of the defined devices
if (_OP_MODE == 0):
    client.bus_init(port=_BUS_PORT, address=_BUS_ADDRESS, baudrate=_BAUDRATE, read_interval=_READ_INTERVAL, register=_MODBUS_REGISTER, register_count=_MODBUS_REGISTER_COUNT, timeout=_MODBUS_TIMEOUT, stopbits=_MODBUS_STOPBITS, bytesize=_MODBUS_BYTESIZE, parity=_MODBUS_PARITY, signed=_MODBUS_SIGNED, endianness=_MODBUS_ENDIANNESS, bit_significance=_MODBUS_BIT_SIGNIFICANCE)
elif (_OP_MODE == 1):
    client.bus_init(port=_BUS_PORT, address=_BUS_ADDRESS, baudrate=_BAUDRATE, read_interval=_READ_INTERVAL)
