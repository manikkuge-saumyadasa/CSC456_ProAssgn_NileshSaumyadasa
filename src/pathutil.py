"""Translate client paths safely between virtual paths and disk paths.

This code makes sure clients can safely access files inside the server's shared folder without being able to 
escape outside that folder.

It does two main things:
1. normalize() cleans up the path the client gives you.
2. to_real() converts that virtual path into a real path on the computer and checks that it stays inside the shared folder.
"""
import os
from errors import FsError


"""
Resolve a client path against cwd without going above virtual root.

Repeated separators and ``.`` are ignored. ``..`` moves to the parent,
but moving above ``/`` raises an error instead of escaping the export.

It receives:
- cwd: the client's current working directory (virtual path).
- user_path: the path the client wants to access.

"""
def normalize(cwd, user_path):
    # If the user_path is empty, it raises an FsError indicating that the path is empty.
    if not user_path:
        raise FsError("empty path")

    # If the user_path starts with "/", it means it's an absolute path, so we start with an empty list of parts.
    # If it doesn't start with "/", it means it's a relative path, so we split the cwd into parts and use that as 
    # the starting point for building the normalized path.
    parts = [] if user_path.startswith("/") else [p for p in cwd.split("/") if p]

    # Split the user_path into components and process each component to build the normalized path.
    # Example: If path is "/home/user" the separator is "/", and the components are ["home", "user"].
    for comp in user_path.split("/"):
        # Ignore empty components and "." which means the current directory.
        if comp in ("", "."):
            continue
        # If the component is "..", it means to go up one directory. If there are no parts left, it raises an FsError.
        if comp == "..":
            # If there are no parts left, it raises an FsError indicating that the path escapes the export root.
            if not parts:
                raise FsError(f"path escapes export root: {user_path}")
            # If there are parts left, it removes the last part from the list, effectively moving up one directory.
            parts.pop()
        else:
            # If the component is a normal directory or file name, it adds it to the list of parts.
            parts.append(comp)

    # Example: If parts is ["home", "user"], the normalized path will be "/home/user".
    return "/" + "/".join(parts)


"""
Map a virtual name to disk and reject symlinks that escape the export.

Resolving links before checking containment prevents an in-root link from
being used to access a target outside the exported directory.

It receives:
- root: the actual shared folder on the computer.
- virtual: the normalized virtual path.
"""
def to_real(root, virtual):
    # Join the root path with the virtual path, and then resolve any symbolic links to get the real path.
    real = os.path.realpath(os.path.join(root, virtual.lstrip("/")))
    # Check if the real path is still within the root directory. If not, it raises an FsError indicating that the path escapes the export root.
    if os.path.commonpath([root, real]) != root:
        raise FsError(f"path escapes export root: {virtual}")
    # If the real path is valid and within the root directory, it returns the real path.
    return real
