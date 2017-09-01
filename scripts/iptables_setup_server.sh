#!/bin/bash
############### Configuration ################
# Flush the current configuration
sudo iptables -F

# Accept connections on the loopback
sudo iptables -A INPUT -i lo -j ACCEPT
sudo iptables -A OUTPUT -o lo -j ACCEPT

# Accept connections via SSH from all network interfaces
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --sport 22 -j ACCEPT

# Allow connections to the NTP server from eth0
sudo iptables -A INPUT -i eth0 -p udp --dport 123 -j ACCEPT
sudo iptables -A OUTPUT -o eth0 -p udp --sport 123 -j ACCEPT

# Accept connections to the OPC UA server from eth0
sudo iptables -A INPUT -i eth0 -p tcp --dport 4840 -j ACCEPT
sudo iptables -A OUTPUT -o eth0 -p tcp --sport 4840 -j ACCEPT

# Accept connections to the DHCP server from wlan0
sudo iptables -A INPUT -i wlan0 -p udp --dport 67 -j ACCEPT
sudo iptables -A OUTPUT -o wlan0 -p udp --sport 67 -j ACCEPT

# Accept connections to the MQTT broker from wlan0
sudo iptables -A INPUT -i wlan0 -p tcp --dport 8883 -j ACCEPT
sudo iptables -A OUTPUT -o wlan0 -p tcp --sport 8883 -j ACCEPT

# Reject all other network traffic
sudo iptables -A INPUT -j REJECT
sudo iptables -A OUTPUT -j REJECT

# Seperate wlan0 from the other network interfaces
sudo iptables -A FORWARD -i wlan0 ! -o wlan0 -j REJECT
sudo iptables -A FORWARD ! -i wlan0 -o wlan0 -j REJECT

######### Set up saving and loading ##########
# Load and save scripts
IPTABLESLOAD=/etc/network/if-pre-up.d/iptablesload
IPTABLESSAVE=/etc/network/if-post-down.d/iptablessave

# Iptables rules
IPTABLESRULES=/etc/network/iptables.rules

# Check, if the load and save scripts already exist and create them if not
if ! [ -f $IPTABLESLOAD ]; then
  sudo touch $IPTABLESLOAD
fi
if ! [ -f $IPTABLESSAVE ]; then
  sudo touch $IPTABLESSAVE
fi

# Make the load and save scripts executable
sudo chmod 777 $IPTABLESLOAD
sudo chmod 777 $IPTABLESSAVE

# Write the load script
sed -e 's/^.*&&& //' > $IPTABLESLOAD << EndLoad
	&&& #!/bin/bash
	&&& iptables-restore < $IPTABLESRULES
	&&& exit 0
EndLoad

# Write the save script
sed -e 's/^.*&&& //' > $IPTABLESSAVE << EndSave
  &&& #!/bin/bash
  &&& iptables-save > $IPTABLESRULES
  &&& exit 0
EndSave
