"""Command-line client for the network file server.

Run it as ``python3 client.py <host> <port> [script_file]``. Without a script
file it prompts for commands; with one it reads commands line by line. In
both cases it sends requests to the server and prints each response. The
server keeps the real working-directory state, and the client shows that
state in its prompt.

``sleep <ms>`` is handled locally to help the experiment scripts time client
arrivals. Blank lines and lines beginning with ``#`` are skipped in scripts.
"""



# Establishes network communication between client and server.
import socket
import sys
# Allows the client to pause execution.
import time
# Call protocol.send_msg() and protocol.recv_msg() to send and receive messages.
from protocol import send_msg, recv_msg

"""
Return a command name and its arguments from one input line.

Commands use whitespace-separated arguments. For "write", the
filename is the first argument and all remaining text is kept together,
including any spaces that belong in the file contents.

Here are some example for write commands and how it handled for other commands:
    write file.txt Hello, world!  ->  ("write", ["file.txt", "Hello, world!"])
    write file.txt                ->  ("write", ["file.txt", ""])
    write file.txt Hello, world! How are you?  ->  ("write", ["file.txt", "Hello, world! How are you?"])

    read file.txt                 ->  ("read", ["file.txt"]) 
"""
def parse(line):
    # Extract the command name, which is the first whitespace-separated token.
    cmd = line.split(None, 1)[0]
    # For "write", keep the filename and all remaining text together as one argument.
    if cmd == "write":
        parts = line.split(None, 2)          # write <file> <text...>
        return cmd, parts[1:]
    # For all other commands, split the line into whitespace-separated tokens.
    return cmd, line.split()[1:]


"""
This is the main function that controls the entire client application.

It handles:
1. Reading command-line arguments.
2. Connecting to the server.
3. Reading commands.
4. Sending commands.
5. Receiving responses.
6. Handling errors.
7. Closing the connection.

This is an infinite loop.

It continuously waits for commands until the user exits or the script finishes.

There are two possible ways to provide commands:
1. Interactive mode.
2. Script mode.

"""
def main():
    # The program expects either three or four command-line arguments.
    # Example :- python3 client.py localhost 8080
    if len(sys.argv) not in (3, 4):
        sys.exit("usage: client.py <host> <port> [script_file]")
    # Extract the host, port
    host, port = sys.argv[1], int(sys.argv[2])
    # If a script file is provided, open it for reading; otherwise, set lines to None to read from input().
    script = open(sys.argv[3]) if len(sys.argv) == 4 else None
    # A script acts as an iterator; None means commands will come from input().
    lines = script if script else None

    # Establish a TCP connection to the server using the provided host and port.
    try:
        sock = socket.create_connection((host, port))
    except OSError as e:
        sys.exit(f"cannot connect to {host}:{port}: {e}")

    # The client maintains its own current working directory (cwd) state, which is updated based on server responses.
    cwd = "/"
    # The main loop reads commands, sends them to the server, and processes responses.
    try:
        while True:

            # If a script file was provided, the program reads the next line.
            if script:
                line = next(lines, None)
                if line is None:
                    break
                # Remove leading and trailing whitespace from the line. 
                line = line.strip()
                # Skip blank lines and comments (lines starting with "#") in the script.
                if not line or line.startswith("#"):
                    continue
                # Echo scripted input so the saved output shows what was run.
                print(f"{cwd}> {line}")
            # If no script file was provided, the program prompts the user for input.
            else:
                # The program prompts the user for input, displaying the current working directory (cwd) in the prompt.
                try:
                    line = input(f"{cwd}> ").strip()
                except EOFError:
                    break
                if not line:
                    continue
            # Parse the input line into a command and its arguments.
            cmd, args = parse(line)

            # This timing helper never goes over the network; it only pauses this client.
            if cmd == "sleep":
                try:
                    # Pause execution for the specified number of milliseconds.
                    time.sleep(int(args[0]) / 1000)
                except (IndexError, ValueError):
                    print("ERROR: usage: sleep <ms>")
                continue

            # The client sends a dictionary containing the command and its arguments.
            send_msg(sock, {"cmd": cmd, "args": args})
            #  After sending the request, the client waits for the server's response.
            # The recv_msg() function receives the response through the same socket.
            resp = recv_msg(sock)

            # If "ok" is True, the operation succeeded.
            if resp.get("ok"):
                # Update the client's current working directory (cwd) based on the server's response.
                cwd = resp.get("cwd", cwd)
                # If the server's response contains an "out" field, print its contents to the console.
                if resp.get("out"):
                    print(resp["out"])
            else:
                print(f"ERROR: {resp.get('err', 'unknown error')}")

            # Terminate the loop if the command is "quit", which indicates that the user wants to exit the client.
            if cmd == "quit":
                break
    except (ConnectionError, OSError):
        print("ERROR: connection to server lost")
        sys.exit(1)
    except KeyboardInterrupt:
        print()
    finally:
        sock.close()


if __name__ == "__main__":
    main()
