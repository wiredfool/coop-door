#!/usr/bin/env python


from flask import Flask, redirect, render_template
from flask_sockets import Sockets

from door import client
client.connect()

app = Flask(__name__)
sockets = Sockets(app)

app.debug = True

@sockets.route('/status')
def ws_status(ws):
    print "starting websocket"
    while True:
        message = ws.receive()
        ws.send(message)
                    
    # UNDONE - 1-> many routing for the socket
    status_socket = client.status_socket()
    print "got status socket"
    while True:
        print "waiting on status message"
        message = status_socket.recv(1024)
        print "sending to socket"
        ws.send(message)
    print "finishing up websocket"
        
        
@app.route('/')
def index():
    print "/"
    return render_template('base.html', page=client.status())
                            
@app.route('/close', methods=['POST'])
def close_door():
    client.close()
    return 'Ok'

@app.route('/open', methods=['POST'])
def open_door():
    client.open()
    return 'Ok'

@app.route('/stop', methods=['POST'])
def stop():
    client.stop()
    return 'Ok'

@app.route('/reload', methods=['POST'])
def refresh():
    client.reload()
    return 'Ok'


