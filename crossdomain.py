import tornado.escape
import tornado.ioloop
import tornado.web
import tornado.websocket
import os.path

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
                (r'/.*', MainHandler),
        ]
        tornado.web.Application.__init__(self, handlers)

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header('Content-Type', 'text/xml; charset=UTF-8')
        self.write('<?xml version="1.0"?>\n<!DOCTYPE cross-domain-policy SYSTEM "http://www.macromedia.com/xml/dtds/cross-domain-policy.dtd">\n<cross-domain-policy>\n<allow-access-from domain="*" secure="false" to-ports="*"/>\n<allow-http-request-headers-from domain="*" headers="*"/>\n<site-control permitted-cross-domain-policies="all" />\n</cross-domain-policy>')

def main():
    app = Application()
    app.listen(843)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()
