"""Implement filesystem commands and their shared path helpers.

Each handler receives the export root, one client's Session, the command
arguments, and the optional experiment delay. It returns displayable text or
raises FsError when the request cannot be completed.
"""
import os
import shutil
import time
from dataclasses import dataclass

from errors import FsError
from pathutil import normalize, to_real


@dataclass
class Session:
    """Per-client state. cwd is a VIRTUAL path; '/' is the export root."""
    cwd: str = "/"


# Each command maps to (minimum args, maximum args, help text).
USAGE = {
    "mkdir":  (1, 1, "mkdir <dir>"),
    "create": (1, 1, "create <file>"),
    "write":  (2, 2, "write <file> <text>"),
    "read":   (1, 1, "read <file>"),
    "ls":     (0, 1, "ls [<dir>]"),
    "cd":     (1, 1, "cd <dir>"),
    "pwd":    (0, 0, "pwd"),
    "mv":     (2, 2, "mv <src> <dst>"),
    "cp":     (2, 2, "cp <src> <dst>"),
    "rm":     (1, 2, "rm [-r] <path>"),
}

"""
Return both the normalized client path and its safe on-disk path.
"""
# Path and timing helpers shared by the command handlers.
def resolve_path(root, s, arg):
    v = normalize(s.cwd, arg)
    return v, to_real(root, v)

"""
Append a child name while keeping virtual root paths well formed.
"""
def _join(v, name):
    return ("" if v == "/" else v) + "/" + name

"""
Check whether a normalized virtual path is equal to or below a parent.
"""
def _inside(child, parent):
    return child == parent or child.startswith(parent.rstrip("/") + "/")

"""
Pause inside a read or write when the server's experiment delay is set.
"""
def _pause(delay_ms):
    if delay_ms > 0:
        time.sleep(delay_ms / 1000)


"""
 Validate source/destination and return virtual and on-disk paths.

For both move and copy, a destination that already names a directory
means the source should be placed inside that directory.
"""
def _src_dst(root, s, cmd, src_arg, dst_arg):

    src_v, src_r = resolve_path(root, s, src_arg)
    if not os.path.lexists(src_r):
        raise FsError(f"no such file or directory: {src_arg}")
    dst_v, dst_r = resolve_path(root, s, dst_arg)
    # If dst is an existing directory, put the source inside it.
    if os.path.isdir(dst_r):
        dst_v = _join(dst_v, src_v.rsplit("/", 1)[1] if src_v != "/" else "")
        dst_r = to_real(root, dst_v)
    if dst_v == src_v:
        raise FsError("source and destination are the same")
    if os.path.isdir(src_r) and _inside(dst_v, src_v):
        raise FsError(f"cannot {cmd} a directory into itself: {src_arg}")
    if os.path.lexists(dst_r):
        raise FsError(f"already exists: {dst_v}")
    if not os.path.isdir(os.path.dirname(dst_r)):
        raise FsError(f"destination directory does not exist: {dst_arg}")
    return src_v, src_r, dst_v, dst_r


# Each command handler receives the export root, session, args, and delay;
# it returns text for the client or raises FsError for a clear user-facing error.
def _mkdir(root, s, a, delay):
    """Create one new directory; its parent must already exist."""
    v, r = resolve_path(root, s, a[0])
    if os.path.lexists(r):
        raise FsError(f"already exists: {v}")
    if not os.path.isdir(os.path.dirname(r)):
        raise FsError(f"no such directory: {a[0]}")
    os.mkdir(r)
    return ""

"""
Create an empty file, failing if the path already exists.
"""
def _create(root, s, a, delay):
    
    v, r = resolve_path(root, s, a[0])
    if os.path.lexists(r):
        raise FsError(f"already exists: {v}")
    if not os.path.isdir(os.path.dirname(r)):
        raise FsError(f"no such directory: {a[0]}")
    # Exclusive-create mode also fails safely if another process creates the path now.
    open(r, "x").close()
    return ""


"""
Replace a file with the supplied text.

The write is split around the optional delay so a reader would see a
partial result if the server did not hold the file's writer lock.
"""
def _write(root, s, a, delay):
    v, r = resolve_path(root, s, a[0])
    if os.path.isdir(r):
        raise FsError(f"is a directory: {v}")
    if not os.path.isdir(os.path.dirname(r)):
        raise FsError(f"no such directory: {a[0]}")
    data = a[1].encode("utf-8")
    mid = len(data) // 2
    # Truncate, write half, pause, and finish; the pause exposes partial-write bugs.
    with open(r, "wb") as f:
        f.write(data[:mid])
        f.flush()
        _pause(delay)
        f.write(data[mid:])
    return ""


"""
Read a file in two pieces, optionally pausing between them.

The delay makes it possible to observe whether a writer can interfere
with a reader that is already holding the shared file lock.
"""
def _read(root, s, a, delay):
    v, r = resolve_path(root, s, a[0])
    if not os.path.exists(r):
        raise FsError(f"no such file: {v}")
    if os.path.isdir(r):
        raise FsError(f"is a directory: {v}")
    with open(r, "rb") as f:
        first = f.read(os.fstat(f.fileno()).st_size // 2)
        _pause(delay)
        rest = f.read()
    return (first + rest).decode("utf-8", errors="replace")


"""
List directory entries in name order with each entry type and size.
"""
def _ls(root, s, a, delay):
    v, r = resolve_path(root, s, a[0] if a else ".")
    if not os.path.exists(r):
        raise FsError(f"no such directory: {v}")
    if not os.path.isdir(r):
        raise FsError(f"not a directory: {v}")
    rows = []
    for e in sorted(os.scandir(r), key=lambda e: e.name):
        if e.is_dir(follow_symlinks=False):
            rows.append(f"d  {'-':>10}  {e.name}")
        else:
            rows.append(f"f  {e.stat(follow_symlinks=False).st_size:>10}  {e.name}")
    return "\n".join(rows) if rows else "(empty)"


"""
Change only this client session’s virtual working directory.
"""
def _cd(root, s, a, delay):
    v, r = resolve_path(root, s, a[0])
    if not os.path.exists(r):
        raise FsError(f"no such directory: {v}")
    if not os.path.isdir(r):
        raise FsError(f"not a directory: {v}")
    s.cwd = v
    return ""


"""
Return the client’s current virtual working directory.
"""
def _pwd(root, s, a, delay):
    return s.cwd

"""
Move or rename a path and update this session if its cwd moved.
"""
def _mv(root, s, a, delay):

    src_v, src_r, dst_v, dst_r = _src_dst(root, s, "move", a[0], a[1])
    shutil.move(src_r, dst_r)
    # If this client was inside the moved directory, update its virtual cwd.
    if _inside(s.cwd, src_v):
        s.cwd = dst_v + s.cwd[len(src_v):]
    return ""

"""
Copy a file or directory tree to a new destination.
"""
def _cp(root, s, a, delay):
    src_v, src_r, dst_v, dst_r = _src_dst(root, s, "copy", a[0], a[1])
    if os.path.isdir(src_r):
        # Keep links as links inside the copy instead of following their targets.
        shutil.copytree(src_r, dst_r, symlinks=True)
    else:
        shutil.copy2(src_r, dst_r)
    return ""

"""
Delete a file or directory; ``-r`` allows recursive directory removal.
"""
def _rm(root, s, a, delay):
    recursive = len(a) == 2
    if recursive and a[0] != "-r":
        raise FsError(f"usage: {USAGE['rm'][2]}")
    v, r = resolve_path(root, s, a[-1])
    if v == "/":
        raise FsError("cannot remove the export root")
    if not os.path.lexists(r):
        raise FsError(f"no such file or directory: {v}")
    if os.path.isdir(r) and not os.path.islink(r):
        if recursive:
            shutil.rmtree(r)
        else:
            try:
                os.rmdir(r)
            except OSError:
                raise FsError(f"directory not empty (use rm -r): {v}")
    else:
        os.remove(r)
    # If the current directory was removed, return this client to its parent.
    if _inside(s.cwd, v):
        s.cwd = v.rsplit("/", 1)[0] or "/"
    return ""


# Central command table keeps supported names and handlers together.
HANDLERS = {
    "mkdir": _mkdir, "create": _create, "write": _write, "read": _read,
    "ls": _ls, "cd": _cd, "pwd": _pwd, "mv": _mv, "cp": _cp, "rm": _rm,
}


