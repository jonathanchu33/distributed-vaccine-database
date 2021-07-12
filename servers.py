import sys
import time
import signal
import socket
import threading
from multiprocessing import Process, Queue
from socket_utils import ClientSocket262, serialize262, deserialize262


# Replica coordination among state machines implemented using:
# Agreement protocol: Schneider, Gries, and Schlichting - Fault Tolerant Broadcasts
# Order protocol: Lamport - Logical clocks (as described by Schneider)

class ServerReplica(Process):
    """State Machine Server Replica class."""
    def __init__(self, ip, port):
        super(ServerReplica, self).__init__()
        # Arguments
        self.ip = ip
        self.port = port

        # Simulated functional status
        self.alive = True

        # Event indicating nonzero client connections
        self.not_idle = threading.Event()

        # Client sockets
        self.client_sockets = {}
        self.send_lock = threading.Lock()

        # Connected clients
        self.connected_clients = set()

        # Local logical clock
        self.lclock = 0
        self.lclock_lock = threading.Lock()

        # Request queues per client; FIFO Channels (Schneider) assumed
        self.request_queues = {}
        self.rq_lock = threading.Lock()

        # Database of vaccine site information
        self.vaccine_availability = {'Harvard University': ['0', '02138']}

        # Initialize server socket
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind((self.ip, self.port))
        self.s.listen(5)

    def run(self):
        """Main execution thread of process."""
        # Dispatch thread to detect simulated failure
        detect_failure_thread = threading.Thread(target=self.detect_simulated_failure, daemon=True)
        detect_failure_thread.start()

        # Dispatch thread to listen for connections
        server_socket_thread = threading.Thread(target=self.serve, daemon=True)
        server_socket_thread.start()

        # Execute requests, according to stability test from order protocol
        execution_queue = {}
        while True:
            # If in simulated fail state, do nothing
            if not self.alive:
                continue

            # Block when there are 0 connections
            self.not_idle.wait()

            # Ensure execution queue is filled with one request from every client
            self.rq_lock.acquire()
            for client_id, request_queue in self.request_queues.items():
                if client_id not in execution_queue:
                    nxt_request = request_queue.get()
                    execution_queue[client_id] = (int(nxt_request['rseqno']),
                                                  client_id, nxt_request)
            self.rq_lock.release()

            # Identify request with lowest request ID (stability test)
            req_id, client_id, fields = min(list(execution_queue.values()),
                                            key = lambda x: (x[0], x[1]))
            while True:
                if fields['transaction'] == 'q':
                    # Quit message case - perform cleanup associated with client
                    self.rq_lock.acquire()
                    del self.request_queues[client_id]
                    self.rq_lock.release()
                    del execution_queue[client_id]
                    self.client_sockets[client_id].client_socket.close()
                    del self.client_sockets[client_id]

                    # Check if server replica now idle
                    if len(self.connected_clients) == 0:
                        self.not_idle.clear()
                else:
                    # Refill execution queue with next request from same client.
                    # If request is not dummy, this verifies agreement protocol
                    # by waiting for receipt of nenxt message from same client.
                    # Otherwise, it refills the execution queue for
                    # re-identification of next stable non-dummy request
                    nxt_request = self.request_queues[client_id].get()
                    execution_queue[client_id] = (int(nxt_request['rseqno']),
                                                  client_id, nxt_request)

                # Execute if request is not a dummy request (stability test)
                if (fields['transaction'] != 'd' and
                    client_id in self.connected_clients) or not self.alive:
                    break

                # Block when there are 0 connections
                self.not_idle.wait()

                # Otherwise, refill execution queue if needed...
                self.rq_lock.acquire()
                for client_id, request_queue in self.request_queues.items():
                    if client_id not in execution_queue:
                        nxt_request = request_queue.get()
                        execution_queue[client_id] = (int(nxt_request['rseqno']),
                                                      client_id, nxt_request)
                self.rq_lock.release()

                # ...and identify request with lowest request ID and repeat
                req_id, client_id, fields = min(list(execution_queue.values()),
                                                key = lambda x: (x[0], x[1]))

            # If in simulated fail state, do nothing
            if not self.alive:
                continue

            # Now prepare to execute request command
            self.lclock_lock.acquire()
            self.lclock += 1
            self.lclock_lock.release()
            action = fields['transaction']
            msg_dict = {
                'transaction': action,
                'lclock': str(self.lclock),
                'rseqno': str(req_id),
            }

            # Execute next command and construct command output
            if action == 'l':
                output = 'Availability,ZIP Code,Site Name\n'
                rows = []
                for site in sorted(self.vaccine_availability.keys()):
                    details = self.vaccine_availability[site]
                    rows.append(','.join(details) + ',' + site)
                output += '\n'.join(rows)

            elif action == 'v':
                site_name = fields['site_name']

                # Check if site exists
                if site_name not in self.vaccine_availability:
                    output = 'Site does not exist. Choose [l] to view all sites.'
                else:
                    site = self.vaccine_availability[site_name]
                    output = 'Availability at {} (ZIP code {}): {}'.format(
                        site_name, site[1], site[0])

            elif action == 'e':
                site_name = fields['site_name']
                vaccine_no = fields['vaccine_no']

                # Check if site exists
                if site_name not in self.vaccine_availability:
                    output = 'Site does not exist. Choose [l] to view all sites.'
                else:
                    self.vaccine_availability[site_name][0] = vaccine_no
                    output = 'Vaccine availability at {} (ZIP code {}) updated to {}.'.format(
                        site_name, self.vaccine_availability[site_name][1], vaccine_no)

            elif action == 'n':
                site_name = fields['site_name']
                zip_code = fields['zip_code']

                # Check if site already exists
                if site_name in self.vaccine_availability:
                    output = '{} already in database.'.format(site_name)
                else:
                    self.vaccine_availability[site_name] = ['0', zip_code]
                    output = '{} (ZIP code {}) added with vaccine availability 0.'.format(
                        site_name, zip_code)

            msg_dict['output_msg'] = output

            # Send output of command to appropriate client
            self.send_lock.acquire()
            self.client_sockets[client_id].send(serialize262(msg_dict))
            self.send_lock.release()

            if test_mode:
                with open('test_log_{}.txt'.format(self.port), 'a') as f:
                    f.write(str(req_id) + ': ' + output + '\n')

    def serve(self):
        """Server socket loop."""
        while True:
            clientsocket, address = self.s.accept()
            clientsocket_object = ClientSocket262(address[0], address[1], clientsocket)
            # Dispatch execution of each client socket in its own thread
            client_thread = threading.Thread(target=self.communicate, args=(clientsocket_object,), daemon=True)
            client_thread.start()

    def communicate(self, scsocket):
        """Main client communication logic."""
        # Receive initial message containing unique client ID
        initial_msg = scsocket.receive()
        initial_fields = deserialize262(initial_msg)
        assert initial_fields['transaction'] == 'i'
        client_id = initial_fields['client_id']

        # Update client connections
        self.rq_lock.acquire()
        self.request_queues[client_id] = Queue()
        self.connected_clients.add(client_id)
        self.rq_lock.release()
        self.not_idle.set()

        # Update logical clock
        self.lclock_lock.acquire()
        self.lclock = max(self.lclock, int(initial_fields['lclock'])) + 1
        self.lclock += 1
        self.lclock_lock.release()

        # Reply with initial ack to update client logical clock
        self.send_lock.acquire()
        if self.alive:
            msg_dict = {'transaction': 'i', 'lclock': str(self.lclock)}
            scsocket.send(serialize262(msg_dict))
        self.send_lock.release()

        # Add socket to dict of sockets
        self.client_sockets[client_id] = scsocket

        # Main communication loop
        while True:
            # Exit if simulated failure
            if not self.alive:
                break

            # Receive message
            incoming_msg = scsocket.receive()
            fields = deserialize262(incoming_msg)
            action = fields['transaction']

            # Update logical clock
            self.lclock_lock.acquire()
            self.lclock = max(self.lclock, int(fields['rseqno'])) + 1
            fields['lclock'] = str(self.lclock)
            self.lclock += 1
            self.lclock_lock.release()

            # Add request to appropriate client request queue
            self.request_queues[client_id].put(fields)

            # Send ack (agreement protocol)
            self.send_lock.acquire()
            scsocket.send(serialize262({'transaction': 'k', 'rseqno': fields['rseqno'], 'lclock': str(self.lclock)}))
            self.send_lock.release()

            # Exit if client is quitting
            if action == 'q':
                break

        if not self.alive:
            # Send failure message
            self.send_lock.acquire()
            msg_dict = {'transaction': 'f', 'lclock': str(self.lclock)}
            scsocket.send(serialize262(msg_dict))
            self.send_lock.release()

            # Wait for client quit signal to clean up sockets
            fields = deserialize262(scsocket.receive())
            while fields['transaction'] != 'q':
                fields = deserialize262(scsocket.receive())

            # Dummy ack to unblock receiving thread of client
            self.send_lock.acquire()
            msg_dict = {'transaction': 'd', 'lclock': str(self.lclock)}
            scsocket.send(serialize262(msg_dict))
            self.send_lock.release()

            # Socket hygiene
            scsocket.client_socket.close()
            del self.client_sockets[client_id]
            self.connected_clients.discard(client_id)
        else:
            assert action == 'q'
            self.connected_clients.discard(client_id)

    def detect_simulated_failure(self):
        """Target to detect simulated server replica failure."""
        while True:
            val = self.failure_notice_queue.get()
            if val:
                self.alive = False
                break


if __name__ == "__main__":
    # Check for correct usage
    if len(sys.argv) != 2 and len(sys.argv) != 3:
        print("Usage: servers.py <# of server replicas>")
        print("Testing Usage: servers.py <# of server replicas> TEST")
        sys.exit()

    if len(sys.argv) == 2 and (not sys.argv[1].isdigit() or int(sys.argv[1]) <= 0):
        print('# of server replicas must be a positive integer!')
        sys.exit()

    # Only used by tests.py
    if len(sys.argv) == 3 and str(sys.argv[2]) != "TEST":
        print("Did you actually mean to test?")
        print("Usage: servers.py <# of server replicas>")
        print("Testing Usage: servers.py <# of server replicas> TEST")
        sys.exit()

    test_mode = len(sys.argv) == 3
    port_num0 = 8892

    num_replicas = int(sys.argv[1])
    sm_replicas = []
    failure_notice_queues = []

    def sigterm_handler(signal, frame):
        # Terminate any subprocesses
        for smr in sm_replicas:
            if smr.is_alive():
                smr.terminate()
        time.sleep(3)
        for smr in sm_replicas:
            smr.close()

        sys.exit()

    if test_mode:
        signal.signal(signal.SIGTERM, sigterm_handler)
        for i in range(num_replicas):
            f = open('test_log_{}.txt'.format(port_num0 + i), 'w')
            f.close()

    try:
        # Initialize server replicas and associated failure simulation channel
        for i in range(num_replicas):
            # localhost used for demonstration
            smr = ServerReplica('localhost', port_num0 + i)
            smr.daemon = True
            failure_notice_queue = Queue()
            smr.failure_notice_queue = failure_notice_queue
            failure_notice_queues.append(failure_notice_queue)
            sm_replicas.append(smr)

        # Start listening for client connections
        for smr in sm_replicas:
            smr.start()

        # Print ip and port of server replicas
        address = "{} state machine replicas initialized at {}.".format(
            num_replicas, ", ".join(["{}:{}".format(smr.ip, smr.port)
                                     for smr in sm_replicas]))
        print(address)

        # Continuously receive input about which server replica to "disable"
        failed = set()
        while True:
            # Prompt for replica index
            index = input('Enter the index of a SM to disable: ').strip()
            while (not index.isdigit() or int(index) >= num_replicas or
                   int(index) < 0 or index in failed):
                if not index.isdigit():
                    prompt = 'Index is a nonegative integer: '
                elif int(index) >= num_replicas or int(index) < 0:
                    prompt = 'Please enter a valid index ([1, N - 1]): '
                else:
                    prompt = f'Replica {index} has already failed. Enter a different SM index: '
                index = input(prompt).strip()

            # Simulate replica failure
            failure_notice_queues[int(index)].put(True)
            failed.add(index)

            # System is only num_replicas - 1 fault-tolerant
            if len(failed) >= num_replicas - 1:
                print('Maximum fault tolerance achieved.')
                break

        # Dummy loop to keep main thread alive after max fault tolerance reached
        while True:
            pass

    except KeyboardInterrupt:
        print("\nCtrl C pressed, cleaning up and exiting...")

        # Terminate any subprocesses
        for smr in sm_replicas:
            if smr.is_alive():
                smr.terminate()
        time.sleep(3)
        for smr in sm_replicas:
            smr.close()

        sys.exit()
