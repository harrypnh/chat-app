#!/bin/sh

## Author - atctam
## Version 1.0 - tested on macOS High Monterey

CPATH="`pwd`"

echo "Start the terminals for clients"
osascript <<-EOD
	tell application "Terminal"
		activate
		do script "cd '$CPATH'; echo \"Start 1st client\"; python3 ChatApp.py"
		delay 0.5
		do script "cd '$CPATH'; echo \"Start 2nd client\"; python3 ChatApp.py config1.txt"
		delay 0.5
		do script "cd '$CPATH'; echo \"Start 3rd client\"; python3 ChatApp.py config2.txt"
		delay 0.5
		do script "cd '$CPATH'; echo \"Start 4th client\"; python3 ChatApp.py config3.txt"
		delay 1.0
	end tell
EOD


echo "Start the server"
osascript <<-EOD
	tell application "Terminal"
		activate
		do script "cd '$CPATH'; python3 Chatserver.py"
		tell application "Terminal" to set custom title of front window to "Chatserver"
	end tell
EOD
