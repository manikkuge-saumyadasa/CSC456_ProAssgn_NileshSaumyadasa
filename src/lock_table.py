"""
Find or create one shared readers-writers lock for each virtual file path.

This code makes sure that each virtual file has its own shared readers-writers lock.

The purpose is to prevent multiple clients from accessing the same file in conflicting ways,
while still allowing clients to work with different files at the same time.

"""
import threading
from rwlock import RWLock

# Creates a semaphore that allows only one thread at a time to access the lock dictionary.
_table_sem = threading.Semaphore(1)
# Creates an empty dictionary.
# It stores: Keys: file paths (strings) and Values: RWLock objects (readers-writers locks).
_locks = {}

"""
Return the shared readers-writers lock for a path, creating it the first time it is used.

The semaphore protects only the dictionary operation. A client waits on
the returned file lock after this function has released the semaphore.
Entries remain until the server exits, avoiding races while clients use them.
"""
def get_lock(path):
    # Acquire the semaphore to ensure exclusive access to the lock dictionary.
    _table_sem.acquire()

    # Check if the lock for the given path already exists in the dictionary.
    # If it does not exist, create a new RWLock and store it in the dictionary
    try:
        # Get the lock for the given path from the dictionary.
        lock = _locks.get(path)
        # If the lock does not exist, create a new RWLock and store it in the dictionary.
        if lock is None:
            lock = _locks[path] = RWLock()
        # Return the lock for the given path.
        return lock
    
    # Finally this block ensures that the semaphore is released even if an error occurs.
    finally:
        _table_sem.release()
