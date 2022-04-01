#!/bin/sh

## Author - atctam
## Version 1.0 - tested on macOS High Monterey

CPATH="`pwd`"

echo "Start the terminal for clients"
osascript <<-EOD
	tell application "Terminal"
		activate
		my makeTab()
		tell application "System Events" to keystroke "2" using {command down}
		delay 0.2
		do script "cd '$CPATH'; echo \"Start 1 client\"; python3 ChatApp.py" in selected tab of window 1	
		activate	
		my makeTab()
		tell application "System Events" to keystroke "3" using {command down}
		delay 0.2
		do script "cd '$CPATH'; echo \"Start 2 client\"; python3 ChatApp.py config1.txt" in selected tab of window 1
		activate				
		my makeTab()
		tell application "System Events" to keystroke "4" using {command down}
		delay 0.2
		do script "cd '$CPATH'; echo \"Start 3 client\"; python3 ChatApp.py config2.txt" in selected tab of window 1
		activate	
		my makeTab()
		tell application "System Events" to keystroke "5" using {command down}
		delay 0.2	
		do script "cd '$CPATH'; echo \"Start 4 client\"; python3 ChatApp.py config3.txt" in selected tab of window 1
	end tell
	on makeTab()
		tell application "System Events" to keystroke "t" using {command down}
		delay 0.5
	end makeTab
EOD



echo "Start the server"
osascript <<-EOD
	tell application "Terminal"
		activate
		do script "cd '$CPATH'; python3 Chatserver.py"
		tell application "Terminal" to set custom title of front window to "Chatserver"
	end tell
EOD
