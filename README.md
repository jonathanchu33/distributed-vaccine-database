## Overview
A simulated distributed database platform for logging COVID vaccine availability. Implements a system of `t` servers which are `t - 1` fail-stop fault-tolerant with ensured distributed consistency and availability, managing server replication using the [state machine approach](#references).

## Requirements
This code was written and tested using Python 3.7.3. Performance with other versions is not guaranteed due to API differences.

## Usage

### Server Deployment
1. Execute `python servers.py [t]`, where `[t]` is a positive integer argument corresponding to the number of simulated servers one wishes to use to deploy the system.
2. To shut down the servers, perform a keyboard interrupt; the servers are otherwise designed to run indefinitely via infinite loops. Note, of course, that this will cause any still-connected clients to fail.

Each server replica is simulated using a separate subprocess; localhost is used as the IP address and ports `8892, 8893, ..., 8892 + (t - 1)` are used by each of the `t` simulated server replicas to listen for connections. If for whatever reason any of these ports are unavailable, one will need to change the lowest port number (`port_num0` in `servers.py`) to `i` such that ports `i, i + 1, ..., i + (t - 1)` are all available.

### Client Usage
1. Execute `python client.py 8892 8893 ... [8892 + (t - 1)]`, where each of the `t` arguments correspond to port numbers on which server replicas are listening.  
For example, if the platform has been deployed with 3 server replicas using `python servers.py 3`, then any client CLI should be established using `python client.py 8892 8893 8894`.
2. To exit a client, use the `[q]` option in the user action menu. **Do not** use keyboard interrupts; these will cause unspecified problems such as hanging clients because resource deallocation (e.g. socket hygiene) is not performed completely and correctly!

### Simulated Server Replica Failure Usage
After the servers are deployed, server replica failure may be simulated at any time by entering an ID into standard input from the command line. Server replica IDs are 0-indexed. For instance, if `t = 3` from above, then entering `1` into standard input corresponds to an instruction to simulate the failure of the second server replica. At most `t - 1` simulated replica failure commands are allowed, because we assume (via implementation) that all failures are fail-stop.

## Design
The motivation for this application was to implement state machine replication to support a working distributed platform. Here we describe technical design choices made in the implementation of Schneider.
- As alluded to above, we assume fail-stop failures for the server replicas in our system, which makes our system `t - 1` fault-tolerant with `t` server replicas.
- We then use the agreement protocol which tolerates fail-stop failures described in Schneider et al. In this protocol, we choose the "bush" broadcast strategy corresponding to Fig. 1(a) in Schneider et al., in which each client is the transmitter and each of the `t` servers are the leaves. This choice of broadcast strategy allowed us to simplify our analysis into the case in which the root transmitter does not fail, because the failure of the transmitter corresponds to the failure of a client, which given our fail-stop failure assumption, is a vacuous case in which the client makes no connection to the service at all and effectively ceases to be a "client" of the system.
- Finally, we use logical clocks (Lamport) to give a total ordering on requests in the system and adapt the stability test for fail-stop failures as described in Schneider.
- To demonstrate the `t - 1` fail-stop fault-tolerant property of our system, we implement a [trigger to simulate server failure](#simulated-server-replica-failure-usage).
- We also implement and use our own custom wire protocol (see `socket_utils.py`) with socket programming.

## Tests
Run `python tests.py`.

## References
1. [Schneider, F.B. *Replication Management using the State Machine Approach*. ACM Press/Addison-Wesley Publishing Co. (1993).](https://pdos.csail.mit.edu/archive/6.824-2007/papers/schneider-rsm.pdf)
2. [Schneider, F.B., D. Gries, and R.D. Schlichting. *Fault-Tolerant Broadcasts*. Science of Computer Programming 4 (1984), 1-15.](https://www.sciencedirect.com/science/article/pii/0167642384900091)
3. [Lamport, L. *Time, clocks and the ordering of events in a distributed system*. CACM 21, 7 (July 1978), 558-565.](https://amturing.acm.org/p558-lamport.pdf)

Developed as a part of Harvard's CS 262 (Distributed Computing).
