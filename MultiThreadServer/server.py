import threading
from threading import Lock
import Queue
import socket
import sys
import time
import json, errno

mutex = Lock()

map_option = {
    'CONNECTION': 1,
    'LOGIN': 2,
    'WAIT_PLAYERS': 3,
    'SET_GAME': 4,
    'SEND_MAP': 5,
    'POSITION': 6,
    'VALIDATION': 7,
    'START': 8,
    'UPDATE_POSITION': 9,
    'FREE_SPACE': 10,
    'SPACES': 11,
    'NEW_MAP': 12,
    'SEND_NEW_MAP': 13,
    'READY_FOR_START': 14,
    'START_AGAIN': 15,
    'OPTION_GAME_FINISHED': 20,
    'DISCONNECT': 99,
    'SUPERUSER': 1000
}

list_ids = []
masterQueue = Queue.Queue()
adminQueue = Queue.Queue()
conn_validated = [0]
conn_players = [0]


class MasterSender(threading.Thread):
    def __init__(self, queue, activeClients):
        threading.Thread.__init__(self)
        self.queue = queue
        self.activeClients = activeClients

    def run(self):
        broadcast = ''
        while True:
            message = self.queue.get()
            print 'MESSAGE', message[0]
            if message is None:
                pass
            if message[1] == 'broadcast':
                for clientsock in self.activeClients:
                    # don't send me back my own message
                    broadcast = message[0]
                    clientsock.conn.send(broadcast)
                    print 'Sending to All' + broadcast
            else:
                print ''
                for clientsock in self.activeClients:
                    # don't send me back my own message
                    if clientsock.client_data['Id'] == message[1]:
                        # print 'Sending to: ' + str(clientsock.client_data['Id']) + ' ' +message[0]
                        clientsock.conn.send(message[0])
                        break

class AdministratorSendStatus(threading.Thread):
    def __init__(self, thread_list, queue, conn):
        threading.Thread.__init__(self)
        self.queue = queue
        self.thread_list = thread_list
        self.conn = conn
    
    def run(self):
        while True:
            message = self.queue.get()
            message = 'Server Output: ' + str(message) + '\n'
            self.conn.send(message)


class AdministratorGetOrders(threading.Thread):
    def __init__(self, thread_list, conn):
        threading.Thread.__init__(self)
        self.thread_list = thread_list
        self.conn = conn
    
    def run(self):
        while True:
            order = self.conn.recv(1024)
            if order == '' or order is None:
                print 'Something wrong with admin'
                self.conn.close()
                raise Exception('empty message error')
            if 'close' in order:
                for clientsock in self.thread_list:
                    clientsock.conn.shutdown()
                    clientsock.conn.close()

class ClientConnection(threading.Thread):
    def __init__(self, conn, idc, typeClient, queue, conn_valid, players):
        self.conn_valid = conn_valid
        self.players = players
        self.conn = conn
        self.queue = queue
        self.client_data = {
            'Id': idc,
            'Map': 'MAPA',
            'Type': typeClient
        }
        threading.Thread.__init__(self)

    def safe_send(self, str):
        try:
            # self.conn.send(str)
            # print 'Sending ' + str + ' to ' + self.client_data['Id']
            self.queue.put((str, self.client_data['Id']))

        except socket.error, e:
            if e.errno == errno.ECONNRESET:
                print 'Client ' + str(self.client_data['Id']) + ' is disconnected'
                self.conn.close()
            else:
                print 'Some unknown error'
                raise socket.errno

    def safe_recv(self, size):
        try:
            a = self.conn.recv(size)
            if a is None or a == '':
                print 'Empty message'
                self.conn.close()
                raise Exception('Error in connection getting empty message ' + str(a))
            return a
        except socket.error, e:
            if e.errno == errno.ECONNRESET:
                print 'Client ' + str(self.client_data['Id']) + ' is disconnected'
                self.conn.close()
            else:
                print 'Some unknown error'
                raise socket.errno

    def generate_map(self):
        return '0000000000000000000000'

    def update_position(self, map_data):
        pass

    def update_free_position(self, map_data):
        map_data[0] = map_data[0]
        return False

    def run(self):
        mssg = {
            'option': 1
        }
        validated = False
        self.safe_send(self.fromDictToJSON(mssg))
        print 'Send 1'
        while True:
            # data = self.conn.recv(1024)
            data = self.safe_recv(1024)
            print 'Data Received', data
            if data == 'close':
                self.queue.put(self.fromDictToJSON({
                    'option': 99,
                    'message': 'server master disconnected server'
                }))
            else:
                map_data = self.fromJSONToDict(data)
                if map_data['option'] == map_option['LOGIN'] and self.players[0] < num_players-1:
                    self.client_data['Type'] = map_data['type']
                    print '3 less players'
                    if self.client_data['Type'] == 0:
                        mutex.acquire()
                        self.players[0] += 1
                        mutex.release()
                        print 'conn_players: ', conn_players, 'vs', self.players[0]
                    self.safe_send(self.fromDictToJSON({'option': map_option['WAIT_PLAYERS']}))
                elif map_data['option'] == map_option['LOGIN'] and self.players[0] >= num_players - 1:
                    print 'in theory 4 players'
                    self.client_data['Type'] = map_data['type']
                    message = {
                        'option': map_option['SET_GAME'],
                        'player_id': self.client_data['Id']
                    }
                    print 'Send using a queue'
                    self.queue.put((self.fromDictToJSON(message), 'broadcast'))
                    print 'All players connected'
                    mapa = self.generate_map()
                    message = {
                        'option': map_option['SEND_MAP'],
                        'matrix size': len(mapa),
                        'map_data': mapa
                    }
                    self.client_data['Map'] = mapa
                    print 'Before Send'
                    self.safe_send(self.fromDictToJSON(message))
                elif map_data['option'] == map_option['POSITION'] and validated:
                    pass
                elif map_data['option'] == map_option['POSITION'] and not validated:
                    while map_data['matrix_pos_x'] != 0 and map_data['matrix_pos_y']!= 0:
                        data = self.safe_recv(1024)
                        map_data = self.fromJSONToDict(data)
                    validated = True
                    self.safe_send(self.fromDictToJSON({'option': map_option['VALIDATION']}))
                    mutex.acquire()
                    self.conn_valid[0] += 1
                    mutex.release()
                    # if self.conn_valid[0] >= num_players:
                    self.queue.put((self.fromDictToJSON({'option': map_option['START']}), 'broadcast'))

                elif map_data['option'] == map_option['UPDATE_POSITION']:
                    self.update_position(map_data)
                    print 'UPDATING IN MAP'
                elif map_data['option'] == map_option['FREE_SPACE']:
                    if self.update_free_position(map_data):
                        self.queue.put((self.fromDictToJSON({'option': map_option['OPTION_GAME_FINISHED'],
                                                            'player_winner': self.client_data['Id']}), 'broadcast'))





    def fromJSONToDict(self, str_json):
        return json.loads(str_json)

    def fromDictToJSON(self, map_json):
        st = json.dumps(map_json)
        return str(len(st)).zfill(4) + st


HOST = '192.168.43.58'  # Symbolic name meaning all available interfaces
PORT = 8897  # Arbitrary non-privileged port

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind((HOST, PORT))
except socket.error as msg:
    print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
    sys.exit()

print 'Socket bind complete'

# Start listening on socket
s.listen(10)
print 'Socket now listening'

clientconnections = []

ids = 1
num_players = 1
actual = 0
ms = MasterSender(masterQueue, clientconnections)
ms.setDaemon(True)
ms.start()
while 1:
    connec, addr = s.accept()
    client_type = 0
    if actual >= num_players:
        client_type = 1
    cc = ClientConnection(connec, ids + 0, client_type + 0, masterQueue, conn_validated, conn_players)
    # cc.daemon = True
    ids += 1
    clientconnections.append(cc)
    print 'Connection added: ', addr
    cc.start()
