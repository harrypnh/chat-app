#!/usr/bin/python3

# Student name and No.: PHAM Nguyen Huan 3035550183
# Development platform: macOS
# Python version: 3.9.7
# Version: 1.0


from tkinter import *
from tkinter import ttk
from tkinter import font
import sys
import socket
import json
import os
import threading

#
# Global variables
#
MLEN = 1000      # assume all commands are shorter than 1000 bytes
USERID = None
NICKNAME = None
SERVER = None
SERVER_PORT = None

server_connected = False
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
active_peer_list = {} # NICKNAME-USERID dict of active peers
all_peer_list = {}    # USERID-NICKNAME dict of all peers which the client has seen
lock = threading.Lock()

#
# Functions to handle user input
#

# read_command() maintains a queue for received commands
# it separates commands if they are sticked together in one recv() call
def read_command(read_socket, recv_command_queue):
    # if the queue is empty, read new commands from recv()
    if recv_command_queue == "":
        try:
            recv_command_queue = read_socket.recv(MLEN).decode()
            # if no command found, let the calling function handles the problem
            if not recv_command_queue:
                return recv_command_queue, recv_command_queue
        except socket.error as err:
            raise Exception("Connection to server broken") from err
    # find the next command in FIFO order from the queue
    end_of_command = 0
    end_of_command_found = False
    brace_level = 0
    for i in range(len(recv_command_queue)):
        if recv_command_queue[i] == "{":
            brace_level += 1
        if recv_command_queue[i] == "}":
            brace_level -= 1
            if brace_level == 0:
                end_of_command_found = True
                end_of_command = i
                break
    # if no command found, let the calling function handles the problem
    if not end_of_command_found:
        return recv_command_queue, recv_command_queue
    # pop the command from the queue
    received_command = recv_command_queue[:end_of_command + 1]
    recv_command_queue = recv_command_queue[end_of_command + 1:]
    return received_command, recv_command_queue

# clean the resources and close the socket to server
def close_socket():
    global server_connected, server_socket, active_peer_list, all_peer_list
    server_socket.close()
    server_connected = False
    active_peer_list = {}
    all_peer_list = {}
    list_print("")

# thread function to listen to the server after joining
def listen(recv_command_queue):
    global server_connected, server_socket, active_peer_list, all_peer_list
    # constantly read new commands from server
    try:
        while True:
            received_command, recv_command_queue = read_command(server_socket, recv_command_queue)
            if not received_command:
                lock.acquire()
                close_socket()
                console_print("Connection to server broken")
                lock.release()
                return
            else:
                received_command = json.loads(received_command)
                # update the peer list after receiving LIST commands
                if received_command["CMD"] == "LIST":
                    lock.acquire()
                    active_peer_list = {}
                    peer_list_str = ""
                    for user in received_command["DATA"]:
                        peer_list_str += user["UN"] + " (" + user["UID"] + "), "
                        active_peer_list[user["UN"]] = user["UID"]
                        all_peer_list[user["UID"]] = user["UN"]
                    list_print(peer_list_str[:-2])
                    lock.release()
                # display the message received from other peers after receiving MSG commands
                elif received_command["CMD"] == "MSG":
                    # identify the message, sender, and type from the MSG command
                    message = received_command["MSG"]
                    sender = received_command["FROM"]
                    message_type = received_command["TYPE"]
                    # display the message according to its type
                    lock.acquire()
                    if message_type == "PRIVATE":
                        chat_print("[" + all_peer_list[sender] + "] " + message, "redmsg")
                    elif message_type == "GROUP":
                        chat_print("[" + all_peer_list[sender] + "] " + message, "greenmsg")
                    elif message_type == "ALL":
                        chat_print("[" + all_peer_list[sender] + "] " + message, "bluemsg")
                    lock.release()
    except:
        # if any exceptions occurs, close the socket to server if it is not closed
        if server_socket.fileno() != -1:
            lock.acquire()
            close_socket()
            console_print("Connection to server broken")
            lock.release()

def do_Join():
    global server_connected, server_socket
    # tell the user if already connected to server
    if server_connected:
        console_print("Already connected to server")
        return
    try:
        # initialise a new socket if the previous one is close
        if (server_socket.fileno() == -1):
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # set the timeout to 2 seconds
        server_socket.settimeout(2)
        server_socket.connect((SERVER, SERVER_PORT))
    # close the socket if timeout or errors occur
    except socket.timeout:
        close_socket()
        console_print("Connection timed out.")
        return
    except socket.error as err:
        close_socket()
        console_print("Failed to connect to server")
        return
    # reset the timeout
    server_socket.settimeout(None)
    server_connected = True
    JOIN_CMD = {
        "CMD": "JOIN",
        "UN": NICKNAME,
        "UID": USERID
    }
    sent = server_socket.send(json.dumps(JOIN_CMD).encode())
    # close the socket if it is broken while sending JOIN commands
    if sent == 0:
        close_socket()
        console_print("Connection to server broken")
        return
    recv_command_queue = ""
    try:
        received_command, recv_command_queue = read_command(server_socket, recv_command_queue)
        if not received_command:
            close_socket()
            console_print("Connection to server broken")
            return
        else:
            received_command = json.loads(received_command)
            if received_command["CMD"] == "ACK":
                # start the listen() thread after receiving ACK_OKAY
                if received_command["TYPE"] == "OKAY":
                    console_print("Successfully connected to server")
                    listen_thread = threading.Thread(target=listen, args=(recv_command_queue,))
                    listen_thread.start()
                # close the socket after receiving ACK_FAIL
                elif received_command["TYPE"] == "FAIL":
                    close_socket()
                    console_print("Username %s already joined" % NICKNAME)
    except:
        # if any exceptions occurs, close the socket to server if it is not closed
        if server_socket.fileno() != -1:
            close_socket()
            console_print("Connection to server broken")

def do_Send():
    lock.acquire()
    global server_connected, server_socket, active_peer_list, all_peer_list
    if not server_connected:
        console_print("Connect to the server first before sending messages")
        lock.release()
        return
    lock.release()
    # take the recipient list and the message to send
    recipients = get_tolist().replace(" ", "")
    send_message = get_sendmsg()
    # check if recipient list and/or message are empty
    if recipients == "" or send_message == "\n":
        if recipients == "":
            console_print("There is no recipient for the message")
        if send_message == "\n":
            console_print("The message input is empty")
        return
    # check if the recipient list is valid
    if recipients == "ALL":
        recipients_UID = []
    else:
        recipients = recipients.split(",")
        lock.acquire()
        if len(recipients) == 1:
            if recipients[0] == NICKNAME or recipients[0] not in active_peer_list:
                if recipients[0] == NICKNAME:
                    console_print("Messages to the current user is not allowed")
                if recipients[0] not in active_peer_list:
                    console_print("[" + recipients[0] + "] Receiving peer not connected")
                lock.release()
                return
            else:
                recipients_UID = [active_peer_list[recipients[0]]]
        else:
            recipients_UID = []
            for recipient in recipients:
                if recipient not in active_peer_list:
                    console_print("[" + recipient + "] Receiving peer not connected")
                elif recipient == NICKNAME:
                    console_print("Messages to the current user is not allowed")
                else:
                    recipients_UID.append(active_peer_list[recipient])
        lock.release()
    SEND_CMD = {
        "CMD": "SEND",
        "MSG": send_message,
        "TO": recipients_UID,
        "FROM": USERID
    }
    lock.acquire()
    sent = server_socket.send(json.dumps(SEND_CMD).encode())
    # close the socket if it is broken while sending MSG commands
    if sent == 0:
        close_socket()
        console_print("Connection to server broken. Message not sent.")
        return
    # display the sent message
    display_message = "[TO: "
    if len(recipients_UID) == 0:
        display_message += "ALL] "
    else:
        for recipient in recipients_UID:
            display_message += all_peer_list[recipient] + ", "
        display_message = display_message[:-2] + "] "
    display_message += send_message
    chat_print(display_message)
    lock.release()

def do_Leave():
    lock.acquire()
    global server_connected, server_socket, active_peer_list, all_peer_list
    # do nothing if not connected to server
    if not server_connected:
        lock.release()
        return
    # otherwise close the socket to server
    close_socket()
    console_print("Leave the chatroom")
    lock.release()

#################################################################################
#Do not make changes to the following code. They are for the UI                 #
#################################################################################

#for displaying all log or error messages to the console frame
def console_print(msg):
    console['state'] = 'normal'
    console.insert(1.0, "\n"+msg)
    console['state'] = 'disabled'

#for displaying all chat messages to the chatwin message frame
#message from this user - justify: left, color: black
#message from other user - justify: right, color: red ('redmsg')
#message from group - justify: right, color: green ('greenmsg')
#message from broadcast - justify: right, color: blue ('bluemsg')
def chat_print(msg, opt=""):
    chatWin['state'] = 'normal'
    chatWin.insert(1.0, "\n"+msg, opt)
    chatWin['state'] = 'disabled'

#for displaying the list of users to the ListDisplay frame
def list_print(msg):
    ListDisplay['state'] = 'normal'
    #delete the content before printing
    ListDisplay.delete(1.0, END)
    ListDisplay.insert(1.0, msg)
    ListDisplay['state'] = 'disabled'

#for getting the list of recipents from the 'To' input field
def get_tolist():
    msg = toentry.get()
    toentry.delete(0, END)
    return msg

#for getting the outgoing message from the "Send" input field
def get_sendmsg():
    msg = SendMsg.get(1.0, END)
    SendMsg.delete(1.0, END)
    return msg

#for initializing the App
def init():
    global USERID, NICKNAME, SERVER, SERVER_PORT

    #check if provided input argument
    if (len(sys.argv) > 2):
        print("USAGE: ChatApp [config file]")
        sys.exit(0)
    elif (len(sys.argv) == 2):
        config_file = sys.argv[1]
    else:
        config_file = "config.txt"

    #check if file is present
    if os.path.isfile(config_file):
        #open text file in read mode
        text_file = open(config_file, "r")
        #read whole file to a string
        data = text_file.read()
        #close file
        text_file.close()
        #convert JSON string to Dictionary object
        config = json.loads(data)
        USERID = config["USERID"].strip()
        NICKNAME = config["NICKNAME"].strip()
        SERVER = config["SERVER"].strip()
        SERVER_PORT = config["SERVER_PORT"]
    else:
        print("Config file not exist\n")
        sys.exit(0)


if __name__ == "__main__":
    init()

#
# Set up of Basic UI
#
win = Tk()
win.title("ChatApp")

# new UI line
def window_close():
    do_Leave()
    win.destroy()
win.protocol("WM_DELETE_WINDOW", window_close)

#Special font settings
boldfont = font.Font(weight="bold")

#Frame for displaying connection parameters
topframe = ttk.Frame(win, borderwidth=1)
topframe.grid(column=0,row=0,sticky="w")
ttk.Label(topframe, text="NICKNAME", padding="5" ).grid(column=0, row=0)
ttk.Label(topframe, text=NICKNAME, foreground="green", padding="5", font=boldfont).grid(column=1,row=0)
ttk.Label(topframe, text="USERID", padding="5" ).grid(column=2, row=0)
ttk.Label(topframe, text=USERID, foreground="green", padding="5", font=boldfont).grid(column=3,row=0)
ttk.Label(topframe, text="SERVER", padding="5" ).grid(column=4, row=0)
ttk.Label(topframe, text=SERVER, foreground="green", padding="5", font=boldfont).grid(column=5,row=0)
ttk.Label(topframe, text="SERVER_PORT", padding="5" ).grid(column=6, row=0)
ttk.Label(topframe, text=SERVER_PORT, foreground="green", padding="5", font=boldfont).grid(column=7,row=0)


#Frame for displaying Chat messages
msgframe = ttk.Frame(win, relief=RAISED, borderwidth=1)
msgframe.grid(column=0,row=1,sticky="ew")
msgframe.grid_columnconfigure(0,weight=1)
topscroll = ttk.Scrollbar(msgframe)
topscroll.grid(column=1,row=0,sticky="ns")
chatWin = Text(msgframe, height='15', padx=10, pady=5, insertofftime=0, state='disabled')
chatWin.grid(column=0,row=0,sticky="ew")
chatWin.config(yscrollcommand=topscroll.set)
chatWin.tag_configure('redmsg', foreground='red', justify='right')
chatWin.tag_configure('greenmsg', foreground='green', justify='right')
chatWin.tag_configure('bluemsg', foreground='blue', justify='right')
topscroll.config(command=chatWin.yview)

#Frame for buttons and input
midframe = ttk.Frame(win, relief=RAISED, borderwidth=0)
midframe.grid(column=0,row=2,sticky="ew")
JButt = Button(midframe, width='8', relief=RAISED, text="JOIN", command=do_Join).grid(column=0,row=0,sticky="w",padx=3)
QButt = Button(midframe, width='8', relief=RAISED, text="LEAVE", command=do_Leave).grid(column=0,row=1,sticky="w",padx=3)
innerframe = ttk.Frame(midframe,relief=RAISED,borderwidth=0)
innerframe.grid(column=1,row=0,rowspan=2,sticky="ew")
midframe.grid_columnconfigure(1,weight=1)
innerscroll = ttk.Scrollbar(innerframe)
innerscroll.grid(column=1,row=0,sticky="ns")
#for displaying the list of users
ListDisplay = Text(innerframe, height="3", padx=5, pady=5, fg='blue',insertofftime=0, state='disabled')
ListDisplay.grid(column=0,row=0,sticky="ew")
innerframe.grid_columnconfigure(0,weight=1)
ListDisplay.config(yscrollcommand=innerscroll.set)
innerscroll.config(command=ListDisplay.yview)
#for user to enter the recipents' Nicknames
ttk.Label(midframe, text="TO: ", padding='1', font=boldfont).grid(column=0,row=2,padx=5,pady=3)
# toentry = Entry(midframe, bg='#ffffe0', relief=SOLID)
toentry = Entry(midframe, relief=SOLID)
toentry.grid(column=1,row=2,sticky="ew")
SButt = Button(midframe, width='8', relief=RAISED, text="SEND", command=do_Send).grid(column=0,row=3,sticky="nw",padx=3)
#for user to enter the outgoing message
# SendMsg = Text(midframe, height='3', padx=5, pady=5, bg='#ffffe0', relief=SOLID)
SendMsg = Text(midframe, height='3', padx=5, pady=5, relief=SOLID)
SendMsg.grid(column=1,row=3,sticky="ew")

#Frame for displaying console log
consoleframe = ttk.Frame(win, relief=RAISED, borderwidth=1)
consoleframe.grid(column=0,row=4,sticky="ew")
consoleframe.grid_columnconfigure(0,weight=1)
botscroll = ttk.Scrollbar(consoleframe)
botscroll.grid(column=1,row=0,sticky="ns")
console = Text(consoleframe, height='10', padx=10, pady=5, insertofftime=0, state='disabled')
console.grid(column=0,row=0,sticky="ew")
console.config(yscrollcommand=botscroll.set)
botscroll.config(command=console.yview)

win.mainloop()
