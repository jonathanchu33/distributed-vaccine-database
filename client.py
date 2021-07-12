import sys
import time
import threading
from datetime import datetime
from multiprocessing import Queue
from socket_utils import ClientSocket262, serialize262, deserialize262


# Replica coordination among state machines implemented using:
# Agreement protocol: Schneider, Gries, and Schlichting - Fault Tolerant Broadcasts
# Order protocol: Lamport - Logical clocks (as described by Schneider)

lclock = 0                      # Logical clock; used to implement order protocol
lclock_lock = threading.Lock()  # Lock for logical clock
request_lock = threading.Lock() # Lock to enforce Broadcast Sequencing Restriction from agreement protocol
quit_flag = False               # Flag indicating that client has quit
sm_replicas = []                # List containing sockets for each server replica
sm_replica_statuses = []        # List containing boolean status of each server replica
ack_queues = []                 # List of queues containing acks from each server replica; used to implement agreement protocol
output_queue = Queue()          # Queue containing outputs of requested commands
client_id = datetime.now().strftime('%Y%m%d%H%M%S%f') # Unique client ID


def choose_action():
    """Display prompt for user and accept a choice."""
    choice = None
    options = ['l', 'v', 'e', 'n', 'q']
    prompt = ('What would you like to do?\n[l] list all vaccine site details;\n'
              '[v] view # of available vaccines at a particular site;\n[e] edit'
              ' vaccine availability at a particular site;\n[n] add a new '
              'vaccine site;\n[q] close the connection and quit.\n')
    while choice not in options:
        choice = input(prompt).strip()
    return choice


def take_action(action):
    """Wire protocol logic based on user's selected action."""
    msg_dict = {'transaction': action, 'client_id': client_id}

    if action == 'v':
        # Prompt for site name
        site_name = input('Please enter the vaccine site name: ').strip()
        msg_dict['site_name'] = site_name

    elif action == 'e':
        # Prompt for site name
        site_name = input('Please enter the vaccine site name: ').strip()
        msg_dict['site_name'] = site_name

        # Prompt for vaccine availability
        p = ('Please enter the number of available vaccines at this site '
             '(or [True/False] for binary availability): ')
        vaccine_no = input(p).strip()
        while not (vaccine_no.isdigit() or vaccine_no == 'True' or
                   vaccine_no == 'False'):
            p = 'Availability must be a nonnegative integer or [True/False]: '
            vaccine_no = input(p).strip()
        msg_dict['vaccine_no'] = vaccine_no

    elif action == 'n':
        # Prompt for site name
        site_name = input('Please enter the vaccine site name: ').strip()
        msg_dict['site_name'] = site_name

        # Prompt for ZIP code
        zip_code = input('Please enter the ZIP code of the site: ').strip()
        while not zip_code.isdigit():
            zip_code = input('ZIP code must be a nonnegative integer: ').strip()
        msg_dict['zip_code'] = zip_code

    return msg_dict


def dummy_request_loop():
    """Target to send dummy requests for logical clock stability test."""
    global lclock

    while True:
        # Send request to server replicas; atomic with respect to request
        # broadcasts according to agreement protocol
        request_lock.acquire()

        ## Update logical clock
        lclock_lock.acquire()
        lclock += 1
        lclock_lock.release()

        ## Use logical clock value as request ID (order protocol)
        request_seqno = lclock

        ## Send request message
        msg_dict = {'transaction': 'd', 'rseqno': str(request_seqno), 'client_id': client_id}
        for i in range(len(sm_replicas)):
            smr = sm_replicas[i]
            # Send request only to active replicas
            if sm_replica_statuses[i]:
                smr.send(serialize262(msg_dict))

        # Check for acks or failure (agreement protocol)
        for i in range(len(sm_replicas)):
            if sm_replica_statuses[i]:
                ack_msg = ack_queues[i].get()
                if ack_msg['transaction'] == 'f':
                    sm_replica_statuses[i] = False

        request_lock.release()

        # Delay between dummy requests
        time.sleep(.1)


def receive_messages(smr_index):
    """Target receiving messages from socket corresponding to smr_index."""
    global lclock

    smr = sm_replicas[smr_index]
    while True:
        # Receive message
        incoming_msg = smr.receive()
        fields = deserialize262(incoming_msg)

        # Break if client quits
        if quit_flag:
            break

        # Update logical clock
        lclock_lock.acquire()
        lclock = max(lclock, int(fields['lclock'])) + 1
        lclock_lock.release()

        # Add to appropriate message queue
        if fields['transaction'] == 'k':
            # Message is an ack (agreement protocol)
            ack_queues[smr_index].put(fields)
        elif fields['transaction'] == 'f':
            # Message is a failure notice (Failure Detection Assumption, Schneider)
            ack_queues[smr_index].put(fields)
            return
        else:
            # Message is a command output, executed upon fulfillment of order protocol
            output_queue.put(fields)


if __name__ == "__main__":
    # Check for correct usage
    print("Enter all port numbers on which server replicas have been initialized, in order for the system to work correctly!")
    print("Example Usage (3 server replicas): client.py 8892 8893 8894")
    if len(sys.argv) < 2:
        print("Must enter at least one server replica.")
        sys.exit()

    # Establish conections to all servers
    for i in range(1, len(sys.argv)):
        # Connect socket
        s = ClientSocket262('localhost', int(sys.argv[i]))
        s.connect()
        sm_replicas.append(s)
        ack_queues.append(Queue())

        # Send initial message with client ID
        s.send(serialize262({'transaction': 'i', 'lclock': str(lclock), 'client_id': client_id}))

        # Detect replica status from response and update logical clock
        fields = deserialize262(s.receive())
        if fields['transaction'] == 'f':
            sm_replica_statuses.append(False)
        else:
            assert fields['transaction'] == 'i'
            sm_replica_statuses.append(True)
        lclock_lock.acquire()
        lclock = max(lclock, int(fields['lclock'])) + 1
        lclock_lock.release()

    print('Connected to {} servers; application starting.\n'.format(len(sys.argv) - 1))

    # Start thread sending dummy requests (order protocol)
    dummy_request_thread = threading.Thread(target=dummy_request_loop, daemon=True)
    dummy_request_thread.start()

    # Start threads receiving command outputs from each server
    receive_threads = []
    for i in range(len(sm_replicas)):
        t = threading.Thread(target=receive_messages, args=(i,), daemon=True)
        t.start()
        receive_threads.append(t)

    # Main while loop
    while True:
        # Prompt user action
        choice = choose_action()
        msg_dict = take_action(choice)

        # Send request to server replicas; atomic with respect to request
        # broadcasts according to agreement protocol
        request_lock.acquire()

        if choice == 'q':
            quit_flag = True

        ## Update logical clock
        lclock_lock.acquire()
        lclock += 1
        lclock_lock.release()

        ## Use lclock value as request ID (order protocol)
        request_seqno = lclock

        ## Send request message
        msg_dict['rseqno'] = str(request_seqno)
        for i in range(len(sm_replicas)):
            smr = sm_replicas[i]
            # Send request only to active replicas unless quitting
            if sm_replica_statuses[i] or choice == 'q':
                smr.send(serialize262(msg_dict))

        if choice == 'q':
            break

        # Check for acks or failure (agreement protocol)
        for i in range(len(sm_replicas)):
            if sm_replica_statuses[i]:
                ack_msg = ack_queues[i].get()
                if ack_msg['transaction'] == 'f':
                    sm_replica_statuses[i] = False

        request_lock.release()

        # Display output to user, after order protocol is fulfilled by server
        queue_seqno = 0
        while queue_seqno != request_seqno:
            # Discard duplicates or outputs to past commands
            msg = output_queue.get()
            queue_seqno = int(msg['rseqno'])

        print('\n' + msg['output_msg'] + '\n')

    # Quit case
    print('Exiting client...')

    # Avoid closing sockets when receive threads are using them to recv
    for t in receive_threads:
        t.join()

    # Socket hygiene
    for smr in sm_replicas:
        smr.client_socket.close()
