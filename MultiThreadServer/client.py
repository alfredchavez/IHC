import socket
import json


def get_json(a, b, c=1, d=1):
    return json.dumps({
        'option':a,
        'type': b,
        'matrix_pos_x': c,
        'matrix_pos_y': d
    })


s = socket.socket(
    socket.AF_INET, socket.SOCK_STREAM)
s.connect(('127.0.0.1', 8888))
while True:
    data = s.recv(1024)
    print data
    str = raw_input()
    words = str.split(',')
    if len(words) == 2:
        s.send(get_json(int(words[0]), int(words[1])))
    elif len(words) == 4:
        s.send(get_json(int(words[0]), int(words[1]), int(words[2]), int(words[3])))


