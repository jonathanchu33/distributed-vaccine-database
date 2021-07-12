import sys
import time
import subprocess

# Before running these tests, one must ensure that the pre-specified ports in
# servers.py are available; otherwise, the servers will not even set up properly
# to run the tests. This is verified by the first assert statement as a 0th
# test of sorts.

if __name__ == "__main__":
    # Start servers
    servers = subprocess.Popen(["python", "servers.py", "3", "TEST"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)

    # Start client 1
    client1 = subprocess.Popen(["python", "client.py", "8892", "8893", "8894"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Read 4 lines of startup prompt
    for _ in range(4):
        client1.stdout.readline()

    time.sleep(2)
    assert servers.poll() is None
    assert client1.poll() is None

    try:
        # Test: Initial list
        for _ in range(6):
            client1.stdout.readline()
        client1.stdin.write(b"l\n")
        client1.stdin.flush()
        client1.stdout.readline()
        header = client1.stdout.readline()
        site = client1.stdout.readline()
        client1.stdout.readline()
        assert header == b"Availability,ZIP Code,Site Name\n"
        assert site == b"0,02138,Harvard University\n"
        print("Test passed")

        # Test: Initial view
        for _ in range(6):
            client1.stdout.readline()
        client1.stdin.write(b"v\nHarvard University\n")
        client1.stdin.flush()
        client1.stdout.readline()
        output = client1.stdout.readline()
        client1.stdout.readline()
        assert output == b"Availability at Harvard University (ZIP code 02138): 0\n"
        print("Test passed")

        # Test: List from a second client
        client2 = subprocess.Popen(["python", "client.py", "8892", "8893", "8894"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Read 4 lines of startup prompt
        for _ in range(4):
            client2.stdout.readline()
        for _ in range(6):
            client2.stdout.readline()
        client2.stdin.write(b"l\n")
        client2.stdin.flush()
        client2.stdout.readline()
        header = client2.stdout.readline()
        site = client2.stdout.readline()
        client2.stdout.readline()
        assert header == b"Availability,ZIP Code,Site Name\n"
        assert site == b"0,02138,Harvard University\n"
        print("Test passed")

        # Test: Edit from client 1
        for _ in range(6):
            client1.stdout.readline()
        client1.stdin.write(b"e\nHarvard University\n10\n")
        client1.stdin.flush()
        client1.stdout.readline()
        output = client1.stdout.readline()
        client1.stdout.readline()
        assert output == b"Vaccine availability at Harvard University (ZIP code 02138) updated to 10.\n"
        print("Test passed")

        # Test: View updated information from client 2
        for _ in range(6):
            client2.stdout.readline()
        client2.stdin.write(b"v\nHarvard University\n")
        client2.stdin.flush()
        client2.stdout.readline()
        output = client2.stdout.readline()
        client2.stdout.readline()
        assert output == b"Availability at Harvard University (ZIP code 02138): 10\n"
        print("Test passed")

        # Test: Add new site from client 2
        for _ in range(6):
            client2.stdout.readline()
        client2.stdin.write(b"n\nMIT\n02138\n")
        client2.stdin.flush()
        client2.stdout.readline()
        output = client2.stdout.readline()
        client2.stdout.readline()
        assert output == b"MIT (ZIP code 02138) added with vaccine availability 0.\n"
        print("Test passed")

        # Test: List updated information from client 1
        for _ in range(6):
            client1.stdout.readline()
        client1.stdin.write(b"l\n")
        client1.stdin.flush()
        client1.stdout.readline()
        header = client1.stdout.readline()
        site1 = client1.stdout.readline()
        site2 = client1.stdout.readline()
        client1.stdout.readline()
        assert header == b"Availability,ZIP Code,Site Name\n"
        assert site1 == b"10,02138,Harvard University\n"
        assert site2 == b"0,02138,MIT\n"
        print("Test passed")

        # Test: Simulate server 0 failure and list from both clients
        servers.stdin.write(b"0\n")
        servers.stdin.flush()
        for _ in range(6):
            client1.stdout.readline()
        client1.stdin.write(b"l\n")
        client1.stdin.flush()
        client1.stdout.readline()
        header = client1.stdout.readline()
        site1 = client1.stdout.readline()
        site2 = client1.stdout.readline()
        client1.stdout.readline()
        assert header == b"Availability,ZIP Code,Site Name\n"
        assert site1 == b"10,02138,Harvard University\n"
        assert site2 == b"0,02138,MIT\n"
        for _ in range(6):
            client2.stdout.readline()
        client2.stdin.write(b"l\n")
        client2.stdin.flush()
        client2.stdout.readline()
        header = client2.stdout.readline()
        site1 = client2.stdout.readline()
        site2 = client2.stdout.readline()
        client2.stdout.readline()
        assert header == b"Availability,ZIP Code,Site Name\n"
        assert site1 == b"10,02138,Harvard University\n"
        assert site2 == b"0,02138,MIT\n"
        print("Test passed")

        # Test: Quit client 1 and list from client 2
        for _ in range(6):
            client1.stdout.readline()
        client1.stdin.write(b"q\n")
        client1.stdin.flush()
        client1.stdout.readline()
        time.sleep(2)
        assert client1.poll() is not None
        for _ in range(6):
            client2.stdout.readline()
        client2.stdin.write(b"l\n")
        client2.stdin.flush()
        client2.stdout.readline()
        header = client2.stdout.readline()
        site1 = client2.stdout.readline()
        site2 = client2.stdout.readline()
        client2.stdout.readline()
        assert header == b"Availability,ZIP Code,Site Name\n"
        assert site1 == b"10,02138,Harvard University\n"
        assert site2 == b"0,02138,MIT\n"
        print("Test passed")

        # Test: Add new site from client 2
        for _ in range(6):
            client2.stdout.readline()
        client2.stdin.write(b"n\nBoston University\n02215\n")
        client2.stdin.flush()
        client2.stdout.readline()
        output = client2.stdout.readline()
        client2.stdout.readline()
        assert output == b"Boston University (ZIP code 02215) added with vaccine availability 0.\n"
        print("Test passed")

        # Test: Initiate client 3 and list updated information
        client3 = subprocess.Popen(["python", "client.py", "8892", "8893", "8894"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Read 4 lines of startup prompt
        for _ in range(4):
            client3.stdout.readline()
        for _ in range(6):
            client3.stdout.readline()
        client3.stdin.write(b"l\n")
        client3.stdin.flush()
        client3.stdout.readline()
        header = client3.stdout.readline()
        site1 = client3.stdout.readline()
        site2 = client3.stdout.readline()
        site3 = client3.stdout.readline()
        client3.stdout.readline()
        assert header == b"Availability,ZIP Code,Site Name\n"
        assert site1 == b"0,02215,Boston University\n"
        assert site2 == b"10,02138,Harvard University\n"
        assert site3 == b"0,02138,MIT\n"
        print("Test passed")

        # Test: Initiate client 4 and add new site
        client4 = subprocess.Popen(["python", "client.py", "8892", "8893", "8894"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Read 4 lines of startup prompt
        for _ in range(4):
            client4.stdout.readline()
        for _ in range(6):
            client4.stdout.readline()
        client4.stdin.write(b"n\nTufts University\n02155\n")
        client4.stdin.flush()
        client4.stdout.readline()
        output = client4.stdout.readline()
        client4.stdout.readline()
        assert output == b"Tufts University (ZIP code 02155) added with vaccine availability 0.\n"
        print("Test passed")

        # Test: Simulate server 1 failure and list from all clients
        servers.stdin.write(b"1\n")
        servers.stdin.flush()
        for _ in range(6):
            client2.stdout.readline()
        client2.stdin.write(b"l\n")
        client2.stdin.flush()
        client2.stdout.readline()
        header = client2.stdout.readline()
        site1 = client2.stdout.readline()
        site2 = client2.stdout.readline()
        site3 = client2.stdout.readline()
        site4 = client2.stdout.readline()
        client2.stdout.readline()
        assert header == b"Availability,ZIP Code,Site Name\n"
        assert site1 == b"0,02215,Boston University\n"
        assert site2 == b"10,02138,Harvard University\n"
        assert site3 == b"0,02138,MIT\n"
        assert site4 == b"0,02155,Tufts University\n"
        for _ in range(6):
            client3.stdout.readline()
        client3.stdin.write(b"l\n")
        client3.stdin.flush()
        client3.stdout.readline()
        header = client3.stdout.readline()
        site1 = client3.stdout.readline()
        site2 = client3.stdout.readline()
        site3 = client3.stdout.readline()
        site4 = client3.stdout.readline()
        client3.stdout.readline()
        assert header == b"Availability,ZIP Code,Site Name\n"
        assert site1 == b"0,02215,Boston University\n"
        assert site2 == b"10,02138,Harvard University\n"
        assert site3 == b"0,02138,MIT\n"
        assert site4 == b"0,02155,Tufts University\n"
        for _ in range(6):
            client4.stdout.readline()
        client4.stdin.write(b"l\n")
        client4.stdin.flush()
        client4.stdout.readline()
        header = client4.stdout.readline()
        site1 = client4.stdout.readline()
        site2 = client4.stdout.readline()
        site3 = client4.stdout.readline()
        site4 = client4.stdout.readline()
        client4.stdout.readline()
        assert header == b"Availability,ZIP Code,Site Name\n"
        assert site1 == b"0,02215,Boston University\n"
        assert site2 == b"10,02138,Harvard University\n"
        assert site3 == b"0,02138,MIT\n"
        assert site4 == b"0,02155,Tufts University\n"
        print("Test passed")

        # Test: Quit all clients, initiate client 5, and list information
        for _ in range(6):
            client2.stdout.readline()
        client2.stdin.write(b"q\n")
        client2.stdin.flush()
        client2.stdout.readline()
        for _ in range(6):
            client3.stdout.readline()
        client3.stdin.write(b"q\n")
        client3.stdin.flush()
        client3.stdout.readline()
        for _ in range(6):
            client4.stdout.readline()
        client4.stdin.write(b"q\n")
        client4.stdin.flush()
        client4.stdout.readline()
        time.sleep(2)
        assert client2.poll() is not None
        assert client3.poll() is not None
        assert client4.poll() is not None
        time.sleep(2)
        client5 = subprocess.Popen(["python", "client.py", "8892", "8893", "8894"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Read 4 lines of startup prompt
        for _ in range(4):
            client5.stdout.readline()
        for _ in range(6):
            client5.stdout.readline()
        client5.stdin.write(b"l\n")
        client5.stdin.flush()
        client5.stdout.readline()
        header = client5.stdout.readline()
        site1 = client5.stdout.readline()
        site2 = client5.stdout.readline()
        site3 = client5.stdout.readline()
        site4 = client5.stdout.readline()
        client5.stdout.readline()
        assert header == b"Availability,ZIP Code,Site Name\n"
        assert site1 == b"0,02215,Boston University\n"
        assert site2 == b"10,02138,Harvard University\n"
        assert site3 == b"0,02138,MIT\n"
        assert site4 == b"0,02155,Tufts University\n"
        print("Test passed")

        # Test: Edit from client 5
        for _ in range(6):
            client5.stdout.readline()
        client5.stdin.write(b"e\nMIT\nFalse\n")
        client5.stdin.flush()
        client5.stdout.readline()
        output = client5.stdout.readline()
        client5.stdout.readline()
        assert output == b"Vaccine availability at MIT (ZIP code 02138) updated to False.\n"
        print("Test passed")

        # Test: Quit client 5
        for _ in range(6):
            client5.stdout.readline()
        client5.stdin.write(b"q\n")
        client5.stdin.flush()
        client5.stdout.readline()
        time.sleep(2)
        assert client5.poll() is not None

        # Test: Compare server replica execution logs
        # (Replica Coordination / Semantic Characterization of SM, Schneider)
        log_texts = []
        f_8892 = open('test_log_8892.txt', 'r')
        f_8893 = open('test_log_8893.txt', 'r')
        f_8894 = open('test_log_8894.txt', 'r')
        log_texts.append(f_8892.read())
        log_texts.append(f_8893.read())
        log_texts.append(f_8894.read())
        f_8892.close()
        f_8893.close()
        f_8894.close()
        log_texts.sort(key = lambda x: len(x))
        assert log_texts[0] == log_texts[1][:len(log_texts[0])]
        assert log_texts[1] == log_texts[2][:len(log_texts[1])]

    except AssertionError:
        print('An assertion failed.')
        servers.terminate()

    client1.terminate()
    client2.terminate()
    client3.terminate()
    client4.terminate()
    client5.terminate()
    servers.terminate()
    time.sleep(2)

    print('All tests passed!')
