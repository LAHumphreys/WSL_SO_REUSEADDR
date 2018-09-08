#!/usr/bin/python2
import socket

serverAddr = socket.getaddrinfo("localhost", 12345, socket.AF_INET6, 0)[0][-1]

s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM) 
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(serverAddr)
s.listen(1)

conn, addr = s.accept()

while 1:
    data = conn.recv(1024)
    if not data:
        print "Out of data!"
    else:
        print "Received: ", data
    break
conn.close()
