"""Serve file-system requests over TCP with one thread per client.

Usage: ``python3 server.py <port> <export_root> [--delay <ms>] [--host <addr>]``.
Each connection gets its own session and working directory. ``fs_ops`` validates
and dispatches commands, ``fs_commands`` implements them, and ``lock_policy``
chooses their per-file lock. The optional delay pauses reads and
writes while they hold a lock, making concurrency easy to observe. Lock waits,
acquisitions, and releases are written to standard output.
"""
import argparse
import os
import socket
import sys
import threading

import lock_table
from errors import FsError
from fs_ops import Session, execute, lock_plan
from logger import log
from protocol import recv_msg, send_msg

# Assign unique client numbers safely when several connections arrive together.
# The semaphore protects the shared counter from simultaneous client threads.
_id_sem = threading.Semaphore(1)
_next_id = 0


"""
Return the next unique client number.
"""
def new_client_id():
    global _next_id
    # Lock the counter while incrementing so every connection gets a distinct ID.
    _id_sem.acquire()
    try:
        _next_id += 1
        return _next_id
    finally:
        # Always unlock the counter, including if returning the ID raises an error.
        _id_sem.release()


"""
Log, acquire, use, and release one file's readers-writers lock.

``r`` permits concurrent readers; ``w`` gives one client exclusive access.
The lock-table semaphore is released before this function waits, so another
file's clients can continue looking up their own locks.
"""
def with_lock(vpath, mode, client_id, cmd, action):
    # Get the lock associated with this virtual path and select its read/write operations.
    lock = lock_table.get_lock(vpath)
    acquire = lock.acquire_read if mode == "r" else lock.acquire_write
    release = lock.release_read if mode == "r" else lock.release_write
    # Log before waiting so lock contention is visible in the server output.
    log("WAIT", client_id, cmd, vpath)
    # A conflicting reader or writer may make this acquisition wait.
    acquire()
    log("GET", client_id, cmd, vpath)
    try:
        return action()
    finally:
        # Release even when the command reports an error, so later clients proceed.
        release()
        log("RELEASE", client_id, cmd, vpath)


"""
Validate and run one request, returning either success or an error response.
"""
def process(root, session, client_id, delay_ms, msg):
    try:
        # Read command and arguments from the decoded request, defaulting args to none.
        cmd, args = msg.get("cmd"), msg.get("args", [])
        # Reject malformed values before lock selection or filesystem dispatch.
        if not isinstance(cmd, str) or not isinstance(args, list) \
                or not all(isinstance(a, str) for a in args):
            raise FsError("malformed request")
        # Ask policy whether this command needs a per-file read or write lock.
        plan = lock_plan(root, session, cmd, args)
        # Execute the same command either way; add a lock only when the policy asks.
        run = lambda: execute(root, session, cmd, args, delay_ms)
        if plan is None:
            # Commands without a planned file lock can run immediately.
            out = run()
        else:
            # A lock plan contains the target path and requested lock mode.
            path, mode = plan
            out = with_lock(path, mode, client_id, cmd, run)
        # Return command output and the session's current working directory.
        return {"ok": True, "out": out, "cwd": session.cwd}
    except FsError as e:
        # Expected command or filesystem errors are returned as client errors.
        return {"ok": False, "err": str(e)}
    # Turn an unexpected failure into a response so one request does not kill the server.
    except Exception as e:
        return {"ok": False, "err": f"internal server error: {e!r}"}


"""
Handle one connection until the client quits or disconnects.
"""
def handle_client(conn, addr, root, delay_ms):
    # Give this connection an ID for logs and an independent working directory.
    client_id = new_client_id()
    log("CONNECT", client_id, "-", f"{addr[0]}:{addr[1]}")
    # Each connection starts at the export root and keeps a private cwd.
    session = Session()
    try:
        while True:
            # Receive one framed request from the connected client.
            msg = recv_msg(conn)
            # Quit is handled here so it does not go through normal command dispatch.
            if isinstance(msg, dict) and msg.get("cmd") == "quit":
                send_msg(conn, {"ok": True, "out": "bye", "cwd": session.cwd})
                break
            if not isinstance(msg, dict):
                # Normalize invalid decoded messages so process returns a useful error.
                msg = {}
            # Process this request and send its success or error response.
            send_msg(conn, process(root, session, client_id, delay_ms, msg))
    except (ConnectionError, OSError, ValueError):
        # A broken connection or frame affects this client only.
        pass
    finally:
        # Close the socket and record the end of this client's connection.
        conn.close()
        log("DISCONNECT", client_id, "-", f"{addr[0]}:{addr[1]}")


"""
Read server settings, validate the export folder, and accept clients.
"""
def main():
    # Define required port/root settings and optional delay/host flags.
    ap = argparse.ArgumentParser(description="Network file system server")
    ap.add_argument("port", type=int)
    ap.add_argument("root", help="directory to export")
    ap.add_argument("--delay", type=int, default=0, metavar="MS",
                    help="read/write sleep MS ms while holding their file lock")
    ap.add_argument("--host", default="0.0.0.0")
    a = ap.parse_args()

    # Canonicalize once so path-containment checks use a consistent root.
    root = os.path.realpath(a.root)
    # Do not start serving if the requested export location is invalid.
    if not os.path.isdir(root):
        sys.exit(f"export root is not a directory: {a.root}")

    # Create, configure, bind, and start listening on the TCP server socket.
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((a.host, a.port))
    srv.listen(64)
    print(f"serving {root} on {a.host}:{a.port} (delay={a.delay} ms)", flush=True)
    try:
        while True:
            # Accept a client and serve it in its own background thread.
            conn, addr = srv.accept()
            # A dedicated daemon thread lets clients work concurrently.
            threading.Thread(target=handle_client, args=(conn, addr, root, a.delay),
                             daemon=True).start()
    except KeyboardInterrupt:
        print("\nshutting down")
    finally:
        # Release the listening socket when the server shuts down.
        srv.close()


if __name__ == "__main__":
    # Run the server entry point only when this file is started as a script.
    main()
