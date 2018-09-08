#!/usr/bin/python2
import socket

serverAddr = socket.getaddrinfo("localhost", 12345, socket.AF_INET6, 0)[0][-1]

c = socket.socket(socket.AF_INET6, socket.SOCK_STREAM) 
c.connect(serverAddr)
c.sendall('Hello World')
