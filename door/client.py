"""

Client side interface via tcp to the coop door

"""

import socket
import multiprocessing

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
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', 8953))


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
