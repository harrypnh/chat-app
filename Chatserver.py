#!/usr/bin/python3

# Student name and No.: PHAM Nguyen Huan 3035550183
# Development platform: macOS
# Python version: 3.9.7
# Version: 1.0

import sys
import socket
import json
import threading

MLEN = 1000
SERVER_PORT = 40350

ACK_OKAY = {"CMD": "ACK", "TYPE": "OKAY"}
ACK_FAIL = {"CMD": "ACK", "TYPE": "FAIL"}

peer_list = []
peer_socket_list = {}

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

# broadcast the peer list to all peers
def broadcast_list():
    LIST_CMD = {
        "CMD": "LIST",
        "DATA": peer_list
    }
    for receiving_peer in peer_socket_list:
        peer_socket_list[receiving_peer].send(json.dumps(LIST_CMD).encode())

# thread function to listen to each peer
def peer_handler(peer, lock):
    peer_socket, peer_address = peer
    peer_info = {"UN": "", "UID": ""}
    recv_command_queue = ""
    try:
        while True:
            received_command, recv_command_queue = read_command(peer_socket, recv_command_queue)
            if not received_command:
                peer_socket.close()
                # if socket is associated to a peer,
                # remove peer from peer_list and send updated peer_list
                # remove associated socket from peer_socket list
                if peer_info["UN"] != "" and peer_info["UID"] != "":
                    print(peer_info["UID"], "at", peer_address, "disconnected")
                    lock.acquire()
                    if peer_info["UID"] in peer_socket_list:
                        peer_list.remove(peer_info)
                        peer_socket_list.pop(peer_info["UID"], None)
                        # send LIST with updated peer list
                        broadcast_list()
                    lock.release()
                else:
                    print(peer_address, "disconnected")
                return

            else:
                received_command = json.loads(received_command)
                if received_command["CMD"] == "JOIN":
                    lock.acquire()
                    # check if peer has already connected
                    if received_command["UID"] in peer_socket_list:
                        # send ACK_FAIL
                        peer_socket.send(json.dumps(ACK_FAIL).encode())
                        print(received_command["UID"], "at", peer_address, "access denied")
                    else:
                        peer_info["UN"] = received_command["UN"]
                        peer_info["UID"] = received_command["UID"]
                        peer_list.append(peer_info)
                        peer_socket_list[peer_info["UID"]] = peer_socket
                        print(peer_info["UID"], "at", peer_address, "successfully joined")
                        # send ACK_OKAY
                        peer_socket.send(json.dumps(ACK_OKAY).encode())
                        # send LIST with updated peer list
                        broadcast_list()
                    lock.release()
                elif received_command["CMD"] == "SEND":
                    MSG_CMD = {
                        "CMD": "MSG",
                        "TYPE": "",
                        "MSG": received_command["MSG"],
                        "FROM": received_command["FROM"]
                    }
                    lock.acquire()
                    # if it is a private message
                    if len(received_command["TO"]) == 1:
                        MSG_CMD["TYPE"] = "PRIVATE"
                        peer_socket_list[received_command["TO"][0]].send(json.dumps(MSG_CMD).encode())
                    
                    # if it is a broadcast message
                    elif len(received_command["TO"]) == 0:
                        MSG_CMD["TYPE"] = "ALL"
                        for receiving_peer in peer_socket_list:
                            if peer_socket_list[receiving_peer] != peer_socket:
                                peer_socket_list[receiving_peer].send(json.dumps(MSG_CMD).encode())

                    # if it is a group message
                    else:
                        MSG_CMD["TYPE"] = "GROUP"
                        for receiving_peer in received_command["TO"]:
                            peer_socket_list[receiving_peer].send(json.dumps(MSG_CMD).encode())
                    lock.release()
                else:
                    print(peer_address, "command unknown")
    except:
        # if any errors occur, close the peer socket if it is not closed
        # broadcast the updated peer list
        if peer_socket.fileno() != -1:
            peer_socket.close()
            if peer_info["UN"] != "" and peer_info["UID"] != "":
                print(peer_info["UID"], "at", peer_address, "disconnected")
                lock.acquire()
                if peer_info["UID"] in peer_socket_list:
                    peer_list.remove(peer_info)
                    peer_socket_list.pop(peer_info["UID"], None)
                    # send LIST with updated peer list
                    broadcast_list()
                lock.release()
            else:
                print(peer_address, "disconnected")

def init(server_port):
    # prepare the server socket for accepting client connections
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.bind(("", server_port))
    except socket.error:
        print("Server's socket bind error")
        sys.exit(1)
    server_socket.listen()

    # constanly accepting new connections
    lock = threading.Lock()
    try:
        while True:
            peer = server_socket.accept()
            print(peer[1], "connection accepted")
            # start a thread to listen to each peer
            peer_thread = threading.Thread(target=peer_handler, args=(peer, lock,))
            peer_thread.start()
    # if any errors occur, close all sockets to peers and the server socket
    except:
        lock.acquire()
        for peer in peer_list:
            peer_socket_list[peer["UID"]].close()
        server_socket.close()
        lock.release()
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        init(SERVER_PORT)
    elif len(sys.argv) == 2 and sys.argv[1].isdecimal():
        init(int(sys.argv[1]))
    else:
        print("Usage: Chatserver [listen port number]")
        sys.exit(1)