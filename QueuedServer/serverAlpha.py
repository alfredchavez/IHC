from threading import Thread
from threading import Lock
import Queue
import socket
import sys
import time
import maze_handler
import json, errno

mutex = Lock()
mutex2 = Lock()

general_queue = Queue.Queue()
error_queue = Queue.Queue()
all_connections = []

player_connections = []
num_players = 0
num_players_validated = 0

viewers_connections = []

program_args = sys.argv

game_started = False

max_players = int(sys.argv[1])
port = int(sys.argv[2])


options = {
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
    'SPACE': 11,
    'NOT_VALID': 12,
    'SEND_NEW_MAP': 13,
    'READY_FOR_START': 14,
    'START_AGAIN': 15,
    'OPTION_GAME_FINISHED': 20,
    'ALL_MAPS': 30,
    'DISCONNECT': 99,
    'SUPERUSER': 1000
}




class ErrorHandler(Thread):
    """ This class handles the errors saved in a Queue """
    def __init__(self, queue):
        Thread.__init__(self)
        self.errors_queue = queue

    def run(self):
        while True:
            error_output = '[-]' + self.errors_queue.get()
            print error_output


class DataSender(Thread):
    """ This class handles the connections where to send a message """

    def __init__(self, clients, queue):
        Thread.__init__(self)
        self.list_of_clients = clients
        self.queue_messages = queue

    def run(self):
        """
        Here we handle the messages that are in the queue of messages
        Messages Structure: Tuple (message, 'broadcast' or client id)
        """

        while True:
            message = self.queue_messages.get()
            if message is None or message is '':
                continue

            if message[0].__class__.__name__ != 'str':
                print 'Sending some not str message'

            if str(message[1]) == 'broadcast':
                self.broadcast_data(message[0])

            else:
                self.send_to_id(message[0], message[1])

    def broadcast_data(self, message):
        for client in self.list_of_clients:
            try:
                client.connection.send(message)
            except socket.error:
                error_queue.put('cannot send value to client with id = ' + str(client.get_id()))

    def send_to_id(self, message , id_connection):
        print 'SENDING ', message, ' TO', id_connection
        for client in self.list_of_clients:
            if client.get_id() == id_connection:
                try:
                    client.connection.send(message)
                except socket.error:
                    error_queue.put('cannot send value to client with id = ' + str(client.get_id()))
                break
        print 'END_SEND'


class UnivReceiver(Thread):
    def __init__(self, connection, threadqueue):
        Thread.__init__(self)
        self.queue = threadqueue
        self.conn = connection
    
    def process_json_input_q(self,jsonstr, json_clean):
        brackets_open = 0
        brackets_close = 0
        json_str = ''
        for ch in jsonstr:
            json_str += ch
            if ch == '{' :
                brackets_open += 1
            elif ch == '}':
                brackets_open -= 1 
                if brackets_open == 0:
                    json_clean.put(json_str[:]) 
                    json_str = ''
    def run(self):
        while(True):
            message_recv = self.conn.recv(1024)
            self.process_json_input_q(message_recv[:], self.queue)



class ClientThread(Thread):
    """ This class handle the client connection, data, etc. ; in a thread """

    def __init__(self, assigned_id, connection, message_queue, list_connected, recvq):
        Thread.__init__(self)
        self.queue = message_queue
        self.recvqueue = recvq
        self.mssg = Queue.Queue()
        self.flag = False
        self.matrix_n = 5
        self.connection = connection
        self.list_of_connected = list_connected
        self.client_data = {
            'id': assigned_id,
            'const_map': None,
            'visible_map': None,
            'type': 1,
            'pos_x': 0,
            'pos_y': 0,
            'all_plays': ''
        }

    def run(self):
        message = {
            'option': 1
        }
        self.safe_send(self.dict_to_json(message))
        while True:
            data = ''
            if not self.recvqueue.empty():
                print 'while1'
                data = self.recvqueue.get()
            if data == None or data == '':
                continue
            print 'DATA: ', data
            print 'after continue'
            try:
                map_data = self.json_to_dict(data)
                if map_data['option'] == options['LOGIN']:
                    self.handle_recv_login(map_data)
                elif map_data['option'] == options['POSITION'] and not self.flag:
                    self.handle_recv_position(map_data)
                elif map_data['option'] == options['POSITION'] and self.flag:
                    pass
                elif map_data['option'] == options['UPDATE_POSITION']:
                    self.handle_recv_update(map_data)
                elif map_data['option'] == options['FREE_SPACE']:
                    self.handle_recv_free_space(map_data)
                elif map_data['option'] == options['DISCONNECT']:
                    self.handle_disconnect()
            except socket.error, e:
                print 'error'
                print e.message
        print 'closing connection'
        self.connection.close()

    def safe_send(self, message):
        general_queue.put((message, self.client_data['id']))

    def safe_broadcast(self, message):
        general_queue.put((message, 'broadcast'))

    def get_id(self):
        return self.client_data['id']

    def safe_recv(self):
        try:
            message_recv = self.connection.recv(1024)
            return message_recv
        except socket.error:
            error_queue.put('cannot receive data from client with id = ' + str(self.client_data['id']))
        return None

    def dict_to_json(self, map_data):
        str_json = json.dumps(map_data)
        return str(len(str_json)).zfill(4) + str_json

    def json_to_dict(self, str_json):
        return json.loads(str_json)

    def generate_map(self):
        """ Generate and set map in client_data """
        cmap, vmap = maze_handler.generate_maze_visible(self.matrix_n, self.matrix_n)
        self.client_data['const_map'] = cmap
        self.client_data['visible_map'] = vmap

    def handle_recv_login(self, map_data):
        """ Handle LOGIN option """

        # Handle type 1 of users (viewers)
        global num_players
        global player_connections
        if map_data['type'] == 1:
            # lists in python are thread safe
            print 'Appending to viewers'
            viewers_connections.append(self)
            print len(viewers_connections)
            if game_started:
                maps_data = ''
                jugadas = ''
                for client in player_connections:
                    maps_data += maze_handler.matrix_to_JSON(client.client_data['const_map']) + '&'
                    jugadas += str(client.get_id()) + '&' + client.client_data['all_plays']
                
                if maps_data[-1] == '&':
                    maps_data = maps_data[:-1]
                
                if jugadas[-1] == '&':
                    jugadas = jugadas[:-1] 

                for client in viewers_connections:
                    print 'SENDING MAP TO CLIENT'
                    client.safe_send(self.dict_to_json({
                        'option': options['ALL_MAPS'],
                        'maps_data': maps_data.replace('true','1').replace('false','0').replace("'", '"'),
                        'jugadas': jugadas
                    }))

        elif map_data['type'] == 0:
            mutex.acquire()
            if num_players + 1 > max_players:
                print 'released 1', num_players, max_players
                mutex.release()
                return
            num_players += 1
            print num_players, 'compare', max_players
            player_connections.append(self)

            if num_players < max_players:
                # send @wait option
                print num_players, 'is minor than', max_players
                self.safe_send(self.dict_to_json({
                    'option': options['WAIT_PLAYERS']
                }))
                print 'released 2'
                mutex.release()
                return
            print 'released 3'
            mutex.release()

            # send @set_game option, then generate and send map
            if num_players == max_players:
                # send @set_game
                for client in player_connections:
                    client.safe_send(self.dict_to_json({
                        'option': options['SET_GAME'],
                        'player_id': client.client_data['id']
                    }))
                time.sleep(3)
                # generate and send map(option @send_map)
                for client in player_connections:
                    print 'client sending: ', client.get_id()
                    client.generate_map()
                    client.safe_send(client.dict_to_json({
                        'option': options['SEND_MAP'],
                        'matrix_size': self.matrix_n,
                        'map_data': maze_handler.matrix_to_JSON(client.client_data['const_map']).replace('true','1').replace('false','0').replace("'", '"')
                    }))
                # send the maps to the viewers
                    

    def handle_recv_position(self, map_data):
        global num_players_validated
        global game_started
        if map_data['matrix_pos_x'] == 0:
            self.flag = True
            self.safe_send(self.dict_to_json({
                'option': options['VALIDATION'],
            }))
            mutex2.acquire()
            num_players_validated += 1
            if num_players_validated < max_players:
                mutex2.release()
                return
            mutex2.release()
            if num_players_validated == max_players:
                # send @set_game
                #maps_data
                maps_data = ''
                game_started = True
                for client in player_connections:
                    client.safe_send(self.dict_to_json({
                        'option': options['START'],
                    }))
                    maps_data += maze_handler.matrix_to_JSON(client.client_data['const_map']) + '&'
                    if maps_data[-1] == '&':
                        maps_data = maps_data[:-1]
                for client in viewers_connections:
                    client.safe_send(self.dict_to_json({
                        'option': options['ALL_MAPS'],
                        'maps_data': maps_data.replace('true','1').replace('false','0').replace("'", '"'),
                        'jugadas': ''
                    }))
                
            

    def handle_recv_update(self, map_data):
        valid = maze_handler.validate_mov(
            self.client_data['pos_x'],
            self.client_data['pos_y'],
            map_data['matrix_pos_x'],
            map_data['matrix_pos_y'],
            (self.client_data['const_map'], self.client_data['visible_map'])
        )
        if valid:
            self.client_data['pos_x'] = map_data['matrix_pos_x']
            self.client_data['pos_y'] = map_data['matrix_pos_y']

    def handle_recv_free_space(self, map_data):
        valid = maze_handler.validate_unlock(
            map_data['matrix_free_x'],
            map_data['matrix_free_y'],
            (self.client_data['const_map'], self.client_data['visible_map']),
            self.client_data['pos_x'],
            self.client_data['pos_y']
        )

        if valid == 2:
            self.client_data['visible_map'][map_data['matrix_free_x']][map_data['matrix_free_y']] = True
            self.client_data['visible_map'][self.client_data['pos_x']][self.client_data['pos_y']] = True
            self.safe_send(self.dict_to_json({
                'option': options['SPACE'],
                'matrix_free_x': map_data['matrix_free_x'],
                'matrix_free_y': map_data['matrix_free_y'],
            }))
            self.safe_broadcast(self.dict_to_json({
                'option': options['OPTION_GAME_FINISHED'],
                'player_winner': self.client_data['id']
            }))

        elif not valid:
            self.safe_send(self.dict_to_json({
                'option': options['NOT_VALID']
            }))
        elif valid:
            self.client_data['visible_map'][map_data['matrix_free_x']][map_data['matrix_free_y']] = True
            self.client_data['visible_map'][self.client_data['pos_x']][self.client_data['pos_y']] = True

            self.safe_send(self.dict_to_json({
                'option': options['SPACE'],
                'matrix_free_x': map_data['matrix_free_x'],
                'matrix_free_y': map_data['matrix_free_y'],
            }))
            self.client_data['all_plays'] += str(map_data['matrix_free_x']) + '&' + str(map_data['matrix_free_y']) + '&'
            for client in viewers_connections:
                client.safe_send(self.dict_to_json({
                    'option': 31,
                    'player_id': self.get_id(),
                    'liberar_x': map_data['matrix_free_x'],
                    'liberar_y': map_data['matrix_free_y'],
                }))

    def handle_disconnect(self):
        # self.connection.shutdown()
        self.connection.close()


HOST = '0.0.0.0'  # Symbolic name meaning all available interfaces
PORT = port  # Arbitrary non-privileged port

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

ids = 1
actual = 0
# ms = MasterSender(masterQueue, clientconnections)
ms = DataSender(all_connections, general_queue)
ms.setDaemon(True)
ms.start()
while 1:
    connec, addr = s.accept()
    newq = Queue.Queue()
    cc = ClientThread(ids + 0, connec, general_queue, all_connections, newq)
    ur = UnivReceiver(connec, newq)
    ur.setDaemon(True)
    ur.start()
    # cc = ClientConnection(connec, ids + 0, client_type + 0, masterQueue, conn_validated, conn_players)
    # cc.daemon = True
    ids += 1
    all_connections.append(cc)
    print 'Connection added: ', addr
    cc.start()








