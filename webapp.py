#!/usr/bin/env python

import web

urls = (
    '/', 'index',
    '/open', 'open_door',
    '/close', 'close_door',
    '/stop', 'stop',
    '/reload', 'reloader',
    )

from door import client
client.connect()

cache = False
t_globals = dict()

render = web.template.render('templates/', cache=cache, 
    globals=t_globals)
render._keywords['globals']['render'] = render


class index:
    def GET(self):
        return render.base(client.status())

class open_door:
    def POST(self):
        client.open()
        raise web.seeother('/')

class close_door:
    def POST(self):
        client.close()
        raise web.seeother('/')

class stop:
    def POST(self):
        client.stop()
        raise web.seeother('/')

class reloader:
    def POST(self):
        client.reload()
        raise web.seeother('/')
    
if __name__ == "__main__":
    app = web.application(urls, globals())
    app.internalerror = web.debugerror
    app.run()
