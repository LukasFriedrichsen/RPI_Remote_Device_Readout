#!/bin/bash
# Flush the firewall settings to allow DNS lookups and the connection to the
# Raspbian repositories
sudo iptables -F

# Update the system
sudo apt-get update
sudo apt-get -y upgrade

# Re-activate the firewall
sudo iptables-restore < /etc/network/iptables.rules

# Restart the system
sudo reboot now
