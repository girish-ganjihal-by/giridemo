import stomp
import requests

from stomp import Connection11, ConnectionListener, Connection12
class Jms(stomp.ConnectionListener):

    def __init__(self):
        self.conn = None

    def connect_AMQ(self):
        self.conn = Connection12([('192.168.0.2', 61613)])


    def connect_JMS(self, message):
        # self.conn.start()
        if self.conn is None:
            self.connect_AMQ()

        self.conn.connect('admin', 'admin')
        self.conn.send(body=message, destination='/queue/PYCAT_INBOUND')
    def initialize_listener(self, queue):
        self.conn.set_listener('', Jms())
        self.conn.start()
        self.conn.connect('admin', 'admin')
        self.conn.subscribe(queue, 1)

    def publish_Message(self):
        response = requests.post('http://127.0.0.1:8161/queue/post', data={"Hello world"})
        print(response)


jms_publish = Jms()
