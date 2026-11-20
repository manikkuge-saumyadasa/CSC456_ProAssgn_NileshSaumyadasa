"""
Choose the per-file readers-writers lock required by each command.

It checks the command, identifies the file path, and decides whether the operation needs:
- A reader lock ("r"): allows multiple clients to read the same file at the same time.
- A writer lock ("w"): gives one client exclusive access to the file.
It returns the file path and lock mode, or None if no file lock is needed.
"""
import os
from fs_commands import HANDLERS, USAGE, resolve_path


"""
Choose at most one normalized file path and lock mode, or return None.

Reads and file copies need a shared reader lock. Writes, file moves, and
file removals need an exclusive writer lock. Directory operations need
no file lock. Invalid argument counts are left for ``execute`` to report.
"""

"""
The function receives four parameters:

root	= Root directory of the virtual filesystem
session	= Client session information
cmd     = Command being executed, such as read or write
args	= Arguments supplied with the command

Example:
cmd = "read" 
args = ["documents/file.txt"]
"""
def lock_plan(root, session, cmd, args):

    # Checks whether the command is specified in the HANDLERS dictionary. If not, it returns None, 
    # indicating that no lock is needed.
    if cmd not in HANDLERS:
        return None
    # It retrieves the expected number of arguments for the command from the USAGE dictionary.
    lo, hi, _ = USAGE[cmd]
    # It checks whether the number of arguments provided falls within the expected range.
    if not lo <= len(args) <= hi:
        return None
    
    # It maps each command to its corresponding lock mode. If the command is not recognized, it returns None.
    mode = {"read": "r", "cp": "r", "write": "w", "mv": "w", "rm": "w"}.get(cmd)
    if mode is None:
        return None

    # It determines the file path to be locked based on the command. For the "rm" command, it takes the last argument 
    # as the path, while for other commands, it takes the first argument.
    arg = args[-1] if cmd == "rm" else args[0]    

    # It resolves the virtual path to a normalized path and checks whether it is a file or directory.
    # v = normalized virtual path, r = resolved real path
    v, r = resolve_path(root, session, arg)        

    # It checks whether the command is "write". If so, it returns None if the resolved path is a directory
    # otherwise it returns the normalized path and lock mode.
    if cmd == "write":
        # Lock even a new file path so concurrent writes cannot race to create it.
        return None if os.path.isdir(r) else (v, mode)
    
    # Read/copy/move/remove use a lock only after checking that the path exists and is a file. 
    # If the resolved path is a file, it returns the normalized path and lock mode. otherwise, it returns None.
    return (v, mode) if os.path.isfile(r) else None
