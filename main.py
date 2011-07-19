import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os.path
import asyncmongo
import time
import functools

from tornado.options import define, options

define('port', default=80, help='run on the given port', type=int)

class Application(tornado.web.Application):
    def __init__(self):
        self.db = asyncmongo.Client(pool_id='mydb', host='127.0.0.1', port=27017, dbname='test')
        handlers = [
                (r'/', MainHandler),
                (r'/add_message', AddHandler),
                (r'/chatsocket', ChatSocketHandler)
        ]
        settings = dict(
            cookie_secret='43oETzKXQAGaYdk6fd8fG1kJFuYh7EQnp2XdTP1o/Vo=',
            template_path=os.path.join(os.path.dirname(__file__), 'templates'),
            static_path=os.path.join(os.path.dirname(__file__), 'static'),
            xsrf_cookies=True,
            autoescape=None
            #debug=True
        )
        tornado.web.Application.__init__(self, handlers, **settings)

class MainHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.application.db.messages.find({}, limit=50, sort=[('time', -1)], callback=self.on_response)

    def on_response(self, response, error):
        if error:
            self.application.db.messages.drop()
            raise tornado.web.HTTPError(500)
        self.render('index.html', messages=response[::-1])

class AddHandler(tornado.web.RequestHandler):
    def post(self):
        logging.info('Post message')
        self.write('Your browser doesn\'t support JavaScript or WebSockets or Flash.');

class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    waiters = set()

    def open(self):
        ChatSocketHandler.waiters.add(self)
        logging.info('Add waiter')

    def on_close(self):
        ChatSocketHandler.waiters.remove(self)
        logging.info('Remove waiter')

    @classmethod
    def send_updates(cls, result, error, chat):
        if error:
            raise tornado.web.HTTPError(500)
        logging.info('Sending message to %d waiters', len(cls.waiters))
        for waiter in cls.waiters:
            try:
                waiter.write_message(chat)
            except:
                logging.error('Error sending message', exc_info=True)

    def on_message(self, message):
        logging.info('Got message %r', message)
        parsed = tornado.escape.json_decode(message)
        text = unicode(parsed['body']).strip()
        if len(text) > 0:
            chat = {
                'body': text[:100],
                'time': time.time()
            }
            chat['html'] = self.render_string('message.html', message=chat)
            callback = functools.partial(ChatSocketHandler.send_updates, chat=chat)
            self.application.db.messages.insert(chat, callback=callback)

def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()
