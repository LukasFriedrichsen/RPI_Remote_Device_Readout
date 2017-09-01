#!/bin/bash
# Paths
LIBMBUS_PATH=/home/pi/libmbus
SO_PATH=/usr/local/lib

# Current version number of libmbus (cf. https://github.com/rscada/libmbus)
LIBMBUS_VERSION=0.8.0

cd $LIBMBUS_PATH/mbus

# Create config.h if it doesn't exist yet
touch ../config.h
echo '#define VERSION "'LIBMBUS_VERSION'"' > ../config.h

# Remove old files
rm *.o
rm *.so

# Compile the necessary components
gcc -fPIC -c mbus.c -o mbus.o
gcc -fPIC -c mbus-protocol.c -o mbus-protocol.o
gcc -fPIC -c mbus-protocol-aux.c -o mbus-protocol-aux.o
gcc -fPIC -c mbus-serial.c -o mbus-serial.o
gcc -fPIC -c mbus-tcp.c -o mbus-tcp.o

# Create the shared library
gcc -shared -o libmbus.so mbus.o mbus-protocol.o mbus-protocol-aux.o mbus-serial.o mbus-tcp.o

# Copy the shared library to SO_PATH
sudo cp libmbus.so $SO_PATH

cd -
