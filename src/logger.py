"""
This code creates a logging system that records events happening in a server, 
especially when multiple clients access files at the same time.

It records:
- The time an event happened.
- Which event happened.
- Which client performed the action.
- Which command was executed.
- Which file or directory was accessed.

"""

import sys
import threading
from datetime import datetime

# Create a semaphore with an initial value of 1.
# It ensures that only one thread writes to the log at a time.
_log_sem = threading.Semaphore(1)

# Store the standard output stream (usually the terminal).
# Log messages will be printed here.
_out = sys.stdout


def log(event, client_id, cmd, path):
    """
    Print one log message containing:
    - Timestamp
    - Event name
    - Client ID
    - Command
    - File or directory path
    """

    # Millisecond precision makes ordering lock events easy to compare.
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    # Format the log message with the timestamp, event name, client ID, command, and path.
    line = f"{ts} {event:<7} client={client_id} cmd={cmd} path={path}"
    # Acquire the semaphore to ensure exclusive access to the log.
    # if another thread is already writing to the log, this thread will wait here until it can acquire the semaphore.
    _log_sem.acquire()
    # Use a try-finally block to ensure the semaphore is released even if an error occurs while printing.
    try:
        # Print the log message to the output stream, flush the buffer to ensure it appears immediately.
        print(line, file=_out, flush=True)
    finally:
        # Release the semaphore so other threads can write to the log.
        _log_sem.release()
