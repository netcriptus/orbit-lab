
import sys
from time import sleep
from socket import socket, AF_INET, SOCK_DGRAM

client = socket(AF_INET, SOCK_DGRAM)
HOST, PORT = "192.168.0.3", 5000

for i in range(20):
    client.sendto("This is a test message\n", (HOST, PORT))