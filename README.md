# RPI_Remote_Device_Readout
Guide and examples on how to remotely read out devices like e.g. power meters with Raspberry Pi single-board computers using a client-server-architectural model and MQTT

## Content:
* Set-up guide: Detailled guide on how to set up the RPIs (both the server- and the node-side)
* Files: Example configuration files as well as programs to read out connected devices (basic implementation includes Modbus RTU and M-Bus support) and process/communicate the data
* Scripts: Bash-scripts to automate certain tasks
* OPC-Server: CODESYS-program to read in user definable variables and expose them via an OPC UA-server (serves as external interface)

The basic implementation uses the CODESYS Control for Raspberry Pi SL (https://store.codesys.com/codesys-control-for-raspberry-pi-sl.html?___store=en&___from_store=default) to set up the OPC UA-server. This solution is commercial and closed source, but has the advantage, that it is highly flexible and can be used for many other tasks as well (since it basically transforms the RPI into a soft-SPS). Nevertheless, there are lots of great open source and complimentary alternatives like the open62541-project (https://github.com/open62541) to achieve the same goal. It could also be considered, not to use OPC UA as external interface at all, but rather to set up a web server or a MQTT connection to AWS, etc. This whole project in general only serves as kind of a template that can be individually adjusted for one's own needs.
