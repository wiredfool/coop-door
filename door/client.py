"""

Client side interface via tcp to the coop door

"""

import socket
import multiprocessing

PORT = 8953
HOST = '127.0.0.1'

sock = None
sock_lock = multiprocessing.Lock()

def _send(msg):
    if sock:
        with sock_lock:
            sock.sendall(msg)
            return sock.recv(1024)
    return False

def connect():
    global sock
    sock = _connect()

def status_socket():
    s = _connect()
    s.sendall('enroll\n')
    return s

def _connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    return s



def status():
    return _send('status\n')
def open():
    return _send('open\n')
def close():
    return _send('close\n')
def stop():
    return _send('stop\n')
def reload():
    return _send('reload\n')
def unload():
    return _send('cleanup\n')
