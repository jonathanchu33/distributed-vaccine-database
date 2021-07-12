import socket
import re

class ClientSocket262:
    """Custom wrapper object for client sockets."""
    def __init__(self, ip, port, clientsocket=None):
        if clientsocket is not None:
            self.client_socket = clientsocket
        else:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ip = ip
        self.port = port

    def connect(self):
        self.client_socket.connect((self.ip, self.port))

    def receive(self):
        """Receives a variable length bytes string literal message."""
        chunks = []
        total_received = 0
        msglen_array = []
        b = None

        # Read length of message in first few bytes
        while b != b'`':
            b = self.client_socket.recv(1)
            msglen_array.append(b.decode('utf-8'))

        del msglen_array[-1] # Delete the backtick delimiter
        msglen = int(''.join(msglen_array))

        # Read message
        while total_received < msglen:
            chunk = self.client_socket.recv(min(msglen - total_received, 2048))
            if chunk == b'':
                raise RuntimeError("Socket connection broken.")
            chunks.append(chunk)
            total_received += len(chunk)

        return b''.join(chunks)

    def send(self, msg):
        """Sends an annotated version of the variable length bytes string literal message."""
        # Compute message length and prepend
        msglen = len(msg)
        bstr_msglen = str(msglen).encode('utf-8')
        msg = bstr_msglen + b'`' + msg
        msglen += len(bstr_msglen) + 1

        # Send message
        total_sent = 0
        while total_sent < msglen:
            sent = self.client_socket.send(msg[total_sent:])
            if sent == 0:
                raise RuntimeError("Socket connection broken.")
            total_sent += sent

        return total_sent

wp = {
    # Protocol related
    'transaction': '0',
    'lclock': '1',
    'rseqno': '2',
    'client_id': '3',
    # Application related
    'site_name': '4',
    'vaccine_no': '5',
    'zip_code': '6',
    # Receipt related
    'output_msg': '7',
}
wp2 = {
    '0': 'transaction',
    '1': 'lclock',
    '2': 'rseqno',
    '3': 'client_id',
    '4': 'site_name',
    '5': 'vaccine_no',
    '6': 'zip_code',
    '7': 'output_msg',
}

def serialize262(field_dict):
    """Custom serialization method for wire protocol."""
    serialized_chunks = []
    for key, value in field_dict.items():
        serialized_chunks.append(wp[key] + ':' + value)
    serialized_str = '`'.join(serialized_chunks) + '`'
    return serialized_str.encode('utf-8')

def deserialize262(str_msg):
    """Custom parsing (deserialization) method for wire protocol."""
    str_msg = str_msg.decode('utf-8')
    field_dict = dict()
    while len(str_msg) > 0:
        index = str_msg.find('`')
        match = re.search('(\d*):(.*)', str_msg[:index], re.ASCII | re.DOTALL)
        field_dict[wp2[match.group(1)]] = match.group(2)
        str_msg = str_msg[index + 1:]
    return field_dict
