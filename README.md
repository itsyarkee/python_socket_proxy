
A socket proxy using epoll implemented by python

Assign a proxy address(host, port) and a desitination address(host, port).
Build a socket client and connect to proxy by tcp protocol. 
All the reqeusts client sends to proxy would be forward to desitination address.
All the responses server sends to proxy would be forward to client.
