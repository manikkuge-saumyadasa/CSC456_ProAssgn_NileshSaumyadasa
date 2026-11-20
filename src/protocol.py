
"""
Encode and decode complete JSON messages for communication
between a client and a server.

TCP sends data as a continuous stream of bytes. It does not
automatically tell us where one message ends and another begins.

To solve this problem, this use a 4 byte length header before
each JSON message.

Message format:
    [4-byte message length][JSON message]

The length tells the receiver exactly how many bytes to read.
"""

import json
import struct

# Maximum allowed message size: 64 MB.
# This prevents the program from trying to receive an extremely
# large message, which could consume too much memory.
MAX_MSG = 64 * 1024 * 1024


"""Receive until n bytes arrive; one TCP read may return only part of them."""
def recv_exact(sock, n):
    # buf is a bytearray that will hold the received bytes. It is mutable and can be extended.
    buf = bytearray()
    # Keep reading from the socket until we have received exactly n bytes.
    while len(buf) < n:
        # Read up to the remaining number of bytes needed (n - len(buf)).
        chunk = sock.recv(n - len(buf))
        # If recv returns an empty bytes object, it means the connection was closed.
        if not chunk:
            raise ConnectionError("connection closed")
        # Append the received chunk to the buffer.
        buf.extend(chunk)
    # Return the buffer as an immutable bytes object.
    return bytes(buf)

"""Serialize an object and send its length header followed by its JSON body."""
def send_msg(sock, obj):
    # data contains the JSON-encoded bytes of the object. The object is serialized to a JSON string and 
    # then encoded to UTF-8 bytes.
    data = json.dumps(obj).encode("utf-8")
    # Send the length of the data as a 4-byte big-endian integer, followed by the actual data.
    sock.sendall(struct.pack(">I", len(data)) + data)


"""Read one complete length-prefixed JSON object from the connection."""
def recv_msg(sock):
    # Read the 4-byte length header using recv_exact and get the message length n.
    # Big-endian unsigned integer format is used to unpack the length.
    (n,) = struct.unpack(">I", recv_exact(sock, 4))
    # If the message is too large, raise a ConnectionError to prevent memory exhaustion.
    if n > MAX_MSG:
        raise ConnectionError(f"message too large: {n}")
    # Read the JSON message body using recv_exact and decode it to a Python object.
    return json.loads(recv_exact(sock, n).decode("utf-8"))


