#!/bin/sh

## Author - atctam
## Version 1.0 - tested on Ubuntu 18.04.3 LTS

echo "Start 1st client"
gnome-terminal -- bash -c "python3 ChatApp.py"

echo "Start 2nd client"
gnome-terminal -- bash -c "python3 ChatApp.py config1.txt"

echo "Start 3rd client"
gnome-terminal -- bash -c "python3 ChatApp.py config2.txt"

echo "Start 4th client"
gnome-terminal -- bash -c "python3 ChatApp.py config3.txt"

echo "Start the server"
gnome-terminal -- bash -c "python3 Chatserver.py; exec bash"
## Add exec bash at the end of the command for keeping the 
## terminal even the command has terminated
