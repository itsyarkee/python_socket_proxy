#!/usr/bin/python
#-*-coding:utf-8-*-

"""
A socket proxy used to forward request-data from src address(host,port)
to dest address(host,port), and forward response-data from dest address
to src address.
request:  src --> proxy --> dest
response: dest --> proxy --> src

author:     iyarkee@gmail.com
version:    1.0 , 2013-01-02
"""

import socket
import select
import logging


#set your proxy address and desitination address here.
proxy_addr = ('', 9090)
dest_addr = ('', 8080)


class SockForward(object):
    """
        For each client, the proxy create a unique sock connecting to dest
    """
    def __init__(self, host, port):
        try:
            self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__sock.connect((host, port))
        except Exception as e:
            logging.exception('')
            self.__sock = None

    def get_sock(self):
        return self.__sock


class ProxyServer(object):
    def __init__(self, host, port):
        self.conns = {} #store all connections, key is fileno
        self.forward_to = {} #store all socket fileno map
        self.__create_server(host, port)

    def __create_server(self, host, port):
        try:
            self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.__sock.bind((host, port))
            self.__sock.listen(1000)
            self.__sock.setblocking(0)

            self.epoll = select.epoll()
            self.epoll.register(self.__sock.fileno(), select.EPOLLIN)
        except Exception as e:
            logging.exception('')
            self.__sock = None

    def start(self):
        if self.__sock is None:
            return
        try:
            while True:
                events = self.epoll.poll(1)
                for fileno, event in events:
                    if fileno == self.__sock.fileno():
                        self.__on_accept()
                    elif event & select.EPOLLIN:
                        self.__on_recv(fileno)
                    elif event & select.EPOLLOUT:
                        self.__on_send(fileno)
                    elif event & select.EPOLLHUP:
                        self.__on_close(fileno)
        finally:
            self.epoll.unregister(self.__sock.fileno())
            self.epoll.close()
            self.__sock.close()

    def __on_accept(self):
        conn, addr = self.__sock.accept()
        logging.info(conn.getpeername())
        conn.setblocking(0)
        self.epoll.register(conn.fileno(), select.EPOLLIN)

        host, port = dest_addr
        forward_sock = SockForward(host, port).get_sock()
        if forward_sock is None:
            return
        forward_sock.setblocking(0)
        self.epoll.register(forward_sock.fileno(), select.EPOLLIN)

        self.conns[conn.fileno()] = conn
        self.conns[forward_sock.fileno()] = forward_sock
        self.forward_to[conn.fileno()] = forward_sock.fileno()
        self.forward_to[forward_sock.fileno()] = conn.fileno()

    def __on_recv(self, fileno):
        try:
            data = self.conns[fileno].recv(1024)
        except Exception as e:
            logging.exception('')
            self.__on_close(fileno)
            return
        try:
            to_fileno = self.forward_to[fileno]
            to_sock = self.conns[to_fileno]
            to_sock.send(data)
        except Exception as e:
            logging.exception('')
            self.__on_close(to_fileno)
            return

    def __on_send(self, fileno):
        pass

    def __on_close(self, fileno):
        try:
            if fileno in self.forward_to:
                to_fileno = self.forward_to[fileno]
            else:
                return
            self.epoll.unregister(fileno)
            self.epoll.unregister(to_fileno)
            self.conns[fileno].close()
            self.conns[to_fileno].close()
            del self.conns[fileno]
            del self.conns[to_fileno]
            del self.forward_to[fileno]
            del self.forward_to[to_fileno]
        except Exception as e:
            logging.exception('')


if __name__ == '__main__':
    try:
        proxy_server = ProxyServer(proxy_addr[0], proxy_addr[1])
        proxy_server.start()
    except Exception as e:
        logging.exception('')
