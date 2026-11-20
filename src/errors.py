"""
This code creates a custom exception called FsError

Its purpose is to handle file-system errors in a controlled manner without crashing the server. 
When an FsError is raised, the server can catch it and send a structured error response to the client, 
indicating that the request failed due to a file-system issue.

"""

class FsError(Exception):
    """A problem the server can safely explain to the client.

    The request handler catches this exception and sends its message in an
    ``{"ok": false, "err": ...}`` response instead of treating it as a crash.
    """
