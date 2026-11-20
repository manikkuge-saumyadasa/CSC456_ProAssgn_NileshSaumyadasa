#!/usr/bin/env bash

# This file contains setup and helper functions used by experiments A through E.
# Each experiment loads this file before starting its server and clients.

# Find the experiment folder, then use it to locate the source code and logs.
EXPERIMENT_FOLDER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_FOLDER="$EXPERIMENT_FOLDER/../src"
LOG_FOLDER="$EXPERIMENT_FOLDER/logs"

# Make sure the folder for server logs exists before an experiment starts.
mkdir -p "$LOG_FOLDER"

# Use these defaults unless the person running the experiment supplies values.
# Example: PORT=5200 DELAY=1000 bash experiments/run_all.sh
PORT="${PORT:-5100}"
DELAY="${DELAY:-2000}"

# Store the background process numbers for all clients in the current experiment.
CLIENT_PROCESS_IDS=()

# Start a temporary server for an experiment.
# The experiment name is used to name its log file.
start_server() {
    local experiment_name="$1"

    # Create temporary folders for exported files and client output.
    EXPORT="$(mktemp -d)"
    WORK="$(mktemp -d)"
    LOG="$LOG_FOLDER/$experiment_name.log"

    # Run the server in the background and save its output in the experiment log.
    python3 "$SOURCE_FOLDER/server.py" "$PORT" "$EXPORT" \
        --delay "$DELAY" > "$LOG" 2>&1 &
    SERVER_PROCESS_ID=$!

    # Clean up the server and temporary folders when this script finishes.
    trap stop_server EXIT

    # Wait for the server's ready message before trying to connect clients.
    for attempt in $(seq 50); do
        if grep -q serving "$LOG" 2>/dev/null; then
            break
        fi
        sleep 0.1
    done
}

# Stop the server and remove this experiment's temporary files.
stop_server() {
    kill "$SERVER_PROCESS_ID" 2>/dev/null
    wait "$SERVER_PROCESS_ID" 2>/dev/null
    rm -rf "$EXPORT" "$WORK"
    echo "(full server log: experiments/logs/$(basename "$LOG"))"
}

# Save client commands in a temporary script and return its file path.
# Example: CLIENT_SCRIPT="$(make_client_script reader.txt 'read file.txt' 'quit')"
make_client_script() {
    local script_name="$1"
    shift

    local script_path="$WORK/$script_name"
    printf '%s\n' "$@" > "$script_path"
    echo "$script_path"
}

# Start one client in the background and save its output in the given file.
# The short pause helps the server assign client numbers in the expected order.
start_client() {
    local script_path="$1"
    local output_path="$2"
    local pause_seconds="${3:-0.1}"

    python3 "$SOURCE_FOLDER/client.py" 127.0.0.1 "$PORT" "$script_path" \
        > "$output_path" 2>&1 &
    CLIENT_PROCESS_IDS+=("$!")

    sleep "$pause_seconds"
}

# Wait until all background clients finish, then clear their saved process numbers.
wait_for_clients() {
    if [ "${#CLIENT_PROCESS_IDS[@]}" -gt 0 ]; then
        wait "${CLIENT_PROCESS_IDS[@]}"
    fi
    CLIENT_PROCESS_IDS=()
}

# Print the current time in seconds, including fractions of a second.
current_time() {
    date +%s.%N
}

# Show WAIT, GET, and RELEASE log entries that match the given text pattern.
show_lock_events() {
    local search_pattern="$1"
    grep -E " (WAIT|GET|RELEASE) " "$LOG" | grep -E "$search_pattern"
}

# Find the line number of a client's lock event for a particular file.
# Arguments: event name (WAIT, GET, or RELEASE), client number, file path.
find_event_line() {
    local event_name="$1"
    local client_number="$2"
    local file_path="$3"

    grep -nE " $event_name +client=$client_number cmd=[a-z]+ path=$file_path\$" \
        "$LOG" | head -1 | cut -d: -f1
}

# Calculate how long a client waited for a file lock, in milliseconds.
# The log's WAIT and GET timestamps mark the start and end of the wait.
measure_lock_wait_ms() {
    local client_number="$1"
    local file_path="$2"

    awk -v client="client=$client_number" -v path="path=$file_path" '
        $3 == client && $5 == path {
            split($1, time_parts, ":")
            timestamp = time_parts[1] * 3600 + time_parts[2] * 60 + time_parts[3]

            if ($2 == "WAIT") {
                wait_started = timestamp
            } else if ($2 == "GET") {
                printf "%d", (timestamp - wait_started) * 1000
                exit
            }
        }
    ' "$LOG"
}

# Print the result of a check after running the supplied command.
# Example: report_check "file exists" test -f "$EXPORT/file.txt"
report_check() {
    local description="$1"
    shift

    if "$@"; then
        echo "PASS: $description"
    else
        echo "FAIL: $description"
    fi
}

# Extract the content printed by the first read command in a client's output.
read_first_file_result() {
    local client_output_path="$1"
    awk '/> read / { getline; print; exit }' "$client_output_path"
}

# Keep the helper names already used by the experiment files.
mk() { make_client_script "$@"; }
launch() { start_client "$@"; }
wait_clients() { wait_for_clients "$@"; }
now() { current_time "$@"; }
excerpt() { show_lock_events "$@"; }
lineno() { find_event_line "$@"; }
waitms() { measure_lock_wait_ms "$@"; }
pass_if() { report_check "$@"; }
read_result() { read_first_file_result "$@"; }
