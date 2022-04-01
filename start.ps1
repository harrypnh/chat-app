<# Author - atctam
## Version 1.0 - tested on Windows 10 #>


Write-Host "Start first client"
Start-Process -WindowStyle Hidden python ChatApp.py

Write-Host "Start second client"
Start-Process -WindowStyle Hidden python "ChatApp.py config1.txt"

Write-Host "Start third client"
Start-Process -WindowStyle Hidden python "ChatApp.py config2.txt"

Write-Host "Start fourth client"
Start-Process -WindowStyle Hidden python "ChatApp.py config3.txt"

Write-Host "Start the Chat server"
Start-Process python Chatserver.py
