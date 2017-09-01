#!/bin/bash
############### Configuration ################
# Flush the current configuration
sudo iptables -F

# Accept connections on the loopback
sudo iptables -A INPUT -i lo -j ACCEPT
sudo iptables -A OUTPUT -o lo -j ACCEPT

# Accept connections via SSH
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --sport 22 -j ACCEPT

# Accept connections from the DHCP client to a DHCP server and the other way round
sudo iptables -A INPUT -p udp --dport 68 -j ACCEPT
sudo iptables -A OUTPUT -p udp --sport 68 -j ACCEPT

# Allow connections to the MQTT broker
sudo iptables -A INPUT -s 192.168.42.1 -p tcp --sport 8883 -j ACCEPT
sudo iptables -A OUTPUT -d 192.168.42.1 -p tcp --dport 8883 -j ACCEPT

# Reject all other network traffic
sudo iptables -A INPUT -j REJECT
sudo iptables -A OUTPUT -j REJECT

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
