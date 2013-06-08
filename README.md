Демо-чат на WebSockets, Tornado, MongoDB
========================================
Читая статьи на хабре о [веб-сокетах](http://en.wikipedia.org/wiki/WebSockets), сильно захотелось что-нибудь написать на них. После долгих поисков я выбрал [Tornado Web Server](http://www.tornadoweb.org/), в качестве сервера, ведь он написан на [Питоне](http://python.org/), да и он похож на [GAE](http://code.google.com/intl/en/appengine/).

Подготовка
----------
Для начала нам понадобятся сам [Python](http://python.org/download/) c [Tornado](https://github.com/facebook/tornado) и [AsyncMongo](https://github.com/bitly/asyncmongo), и [MongoDB](http://www.mongodb.org/downloads). У меня всё с успехом установилось как на Windows 7 x64, так и на Debian 6 x86. Для установки библиотек для питона помогает [easy_install](http://packages.python.org/distribute/easy_install.html).
Кстати, в зависимостях asyncmongo есть pymongo, которому понадобятся при установке компилятор (gcc) и заголовочные файлы (python-dev).

Сервер
------
Наш сервер будет выполнять следующие вещи:
- Выдача главной страницы
- Выдача статики
- Обслуживание сокета
- Соединение с базой
- Выдача сообщения о том, что у нашего пользователя нет флэша/js/ws

```python
class Application(tornado.web.Application):
    def __init__(self):
        self.db = asyncmongo.Client(pool_id='mydb', host='127.0.0.1', port=27017, dbname='test')
        handlers = [
                (r'/', MainHandler),
                (r'/add_message', AddHandler),
                (r'/chatsocket', ChatSocketHandler)
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), 'templates'),
            static_path=os.path.join(os.path.dirname(__file__), 'static'),
        )
        tornado.web.Application.__init__(self, handlers, **settings)
```
`/add_message` - это action у формы сообщения, ведь именно туда пойдет наш консерватор.

Главная берет последние 50 сообщений из БД, и после их получения парсит шаблон.
```python
class MainHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.application.db.messages.find({}, limit=50, sort=[('time', -1)], callback=self.on_response)

    def on_response(self, response, error):
        if error:
            raise tornado.web.HTTPError(500)
        self.render('index.html', messages=response[::-1])
```
Для нашего нерадивого пользователя мы покажем это:
```python
class AddHandler(tornado.web.RequestHandler):
    def post(self):
        logging.info('Post message')
        self.write('Your browser doesn\'t support JavaScript or WebSockets or Flash.');
```
С сокетом кода выйдет чуть поболее.
Для началам нам понадобиться переменная для хранения всех подключенных, 
```python
class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    waiters = set()

    def open(self):
        ChatSocketHandler.waiters.add(self)
        logging.info('Add waiter')

    def on_close(self):
        ChatSocketHandler.waiters.remove(self)
        logging.info('Remove waiter')
```
При получении сообщения, мы создаем объект с датой, текстом, а также HTML представлением (которое вполне логично засунуть в клиент). Затем запускаем операцию добавления, заранее запихав в callback объект с сообщением.
```python
    def on_message(self, message):
        logging.info('Got message %r', message)
        parsed = tornado.escape.json_decode(message)
        chat = {
            'body': parsed['body'],
            'time': time.time()
        }
        chat['html'] = self.render_string('message.html', message=chat)
        callback = functools.partial(ChatSocketHandler.send_updates, chat=chat)
        self.application.db.messages.insert(chat, callback=callback)
```
И как только сообщение добавится в БД, рассылаем его всем клиентам.
```python
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
```

Клиент
------
Клиентский html состоит из простенькой формы.
Javscript же вешает свой обработчик на событие submit и нажатие Enter, для отправки сообщения  в сокет.
```javascript
updater.socket.send(JSON.stringify(message));
```
Подключение к сокету, который ожидает на том же хосте и порту.
```javascript
updater.socket = new WebSocket('ws://'+document.location.host+'/chatsocket');
```
Обработка входящих сообщений.
```javascript
updater.socket.onmessage = function(event) {
  updater.showMessage(JSON.parse(event.data));
}
```
Обработка закрытия сокета.
```javascript
updater.socket.onclose = function () {
	if (confirm('Socket disconnected.\nReload this page?'))
		document.location.reload();
}
```

### Клиент без поддержки WebSocket
Для него на стороне клиента мы воспользуемся [web-socket-js](https://github.com/gimite/web-socket-js).
А на стороне сервер нам придется повесить сервер для статической страницы на 843 порт, отдающий `crossdomain.xml`:
```xml
<?xml version="1.0"?>
<!DOCTYPE cross-domain-policy SYSTEM "http://www.macromedia.com/xml/dtds/cross-domain-policy.dtd">
<cross-domain-policy>
	<allow-access-from domain="*" secure="false" to-ports="*"/>
	<site-control permitted-cross-domain-policies="master-only" />
</cross-domain-policy>
```
А какой сервер лучше всех отдает статику? [nginx](http://www.nginx.ru/), примерно такого конфига:
```nginx
server {
	listen 843;
	location / {
		rewrite ^(.*)$ /crossdomain.xml;
	}
	error_page 400 /crossdomain.xml;
	location = /crossdomain.xml {
		root /var/www/static;
	}
}
```
