# Start a temporary server, run the Part 1 command sequence, and save client/server output.

# Locate the test assets relative to this script and allow a custom test port.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; PORT="${PORT:-5101}"
# Use a fresh export directory so the test does not alter user files.
EXPORT=$(mktemp -d)
# Run the server in the background and redirect its output to a log file.
python3 "$HERE/../src/server.py" "$PORT" "$EXPORT" > "$HERE/part1_server.log" 2>&1 &
# Remember the server process and give it a moment to bind its port.
SP=$!; sleep 0.7
python3 "$HERE/../src/client.py" 127.0.0.1 "$PORT" "$HERE/part1_commands.txt" | tee "$HERE/part1_output.txt"
# Stop the temporary server and remove its exported test files.
kill $SP; wait $SP 2>/dev/null; rm -rf "$EXPORT"
