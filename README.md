# CSC456 Network File System

A small network file server written in Python. The server exports one directory; clients connect over TCP and manage files inside it with shell-like commands. Each client has its own virtual working directory.

## Start the program

Run these commands from the project folder. The shared files will live in its `export/` subfolder.

Open one terminal and start the server:

```sh
mkdir -p export
python3 src/server.py 5001 export
```

In another terminal, start a client:

```sh
python3 src/client.py localhost 5001
```

To run commands from a script instead of typing them:

```sh
python3 src/client.py localhost 5001 path/to/commands.txt
```

The server also accepts `--delay <milliseconds>`, which pauses each read and write while its file lock is held. This is useful for observing concurrency:

```sh
python3 src/server.py 5001 export --delay 2000
```

## Commands

`mkdir <dir>`, `create <file>`, `write <file> <text>`, `read <file>`, `ls [dir]`, `cd <dir>`, `pwd`, `mv <src> <dst>`, `cp <src> <dst>`, `rm <path>`, `rm -r <dir>`, and `quit`.

Paths are relative to the client's current directory unless they start with `/`. The virtual `/` always means the server's export root. Paths that escape that root are rejected. If the destination of `mv` or `cp` is a directory, the source is placed inside it.

## How the project is organized

| File | Responsibility |
| --- | --- |
| `src/server.py` | Accepts TCP connections, gives each client its own thread and session, dispatches commands, and logs lock events. |
| `src/client.py` | Reads typed or scripted commands, sends requests, and prints server responses. The `sleep <ms>` command is local to the client and only used by experiments. |
| `src/protocol.py` | Encodes JSON messages with a four-byte length prefix so message boundaries do not depend on newlines. |
| `src/fs_ops.py` | Validates commands, dispatches to their handlers, and translates file-system errors. |
| `src/fs_commands.py` | Implements each file and directory command and shared path helpers. |
| `src/lock_policy.py` | Decides which per-file reader or writer lock a command needs. |
| `src/pathutil.py` | Converts client paths to normalized virtual paths and verifies resolved paths stay inside the export root. |
| `src/rwlock.py` | Implements the readers-writers lock using semaphores and a shared reader count. |
| `src/lock_table.py` | Stores one readers-writers lock per normalized file path; a semaphore protects the table. |
| `src/logger.py` | Writes timestamped, non-interleaved `WAIT`, `GET`, and `RELEASE` lock events. |
| `src/errors.py` | Defines user-facing filesystem errors returned by the server. |
| `export/` | The default shared folder when following the run commands above. |
| `tests/` | Contains the Part 1 command script and its Bash runner. |
| `experiments/` | Contains one script per concurrency scenario and shared helpers in `common.sh`. |

## Concurrency behavior

Multiple readers may hold a file's lock at the same time. A writer gets exclusive access and waits for active readers or writers to finish. Reads and writes to different files use different locks. File `read`, file-source `cp`, `write`, file `mv`, and file `rm` use locks; directory operations do not, as specified by the assignment. Every command takes at most one file lock.

The lock uses the textbook reader-preference semaphore solution. As a result, a continuing stream of new readers can keep a waiting writer from acquiring the lock. The assignment asks for this behavior to be explained in the report.

## Run the supplied scripts

These targets require Bash:

```sh
make part1
make experiments
```

`make part1` runs `tests/part1_commands.txt` against a temporary export directory and saves the client output and server log under `tests/`. `make experiments` runs the demonstrations in order:

- `exp_a_parallel_readers.sh`: multiple readers of one file overlap.
- `exp_b_writers.sh`: writers serialize and reads do not observe partial writes.
- `exp_c_different_files.sh`: activity on one file does not block a different file.
- `exp_d_writer_waits.sh`: a writer waits for all current readers.
- `exp_e_starvation.sh`: optional demonstration of reader preference delaying a writer.

Each experiment writes its server log under `experiments/logs/`. `PORT` and `DELAY` can be set to override the defaults, for example `PORT=5200 DELAY=1000 make experiments`.