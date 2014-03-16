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
    # UNDONE - 1-> many routing for the socket
    status_socket = client.status_socket()
    while True:
        message = status_socket.recv(1024)
        ws.send(message)
        
@app.route('/')
def index():
    return render_template('base.html', page=client.status())
                            
@app.route('/close', methods=['POST'])
def close_door():
    client.close()
    return redirect('/')

@app.route('/open', methods=['POST'])
def open_door():
    client.open()
    return redirect('/')

@app.route('/stop', methods=['POST'])
def stop():
    client.stop()
    return redirect('/')

@app.route('/reload', methods=['POST'])
def refresh():
    client.reload()
    return redirect('/')


