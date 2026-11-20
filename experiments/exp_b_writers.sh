# Experiment B: verify that writes to one file are exclusive and readers do not
# observe a file halfway through a write.

# Load common setup and helper functions used by every concurrency experiment.
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# Start an isolated server and save its events in experiments/logs/exp_b.log.
start_server exp_b

# Make three distinct 40-character file versions. Distinct repeated characters
# make partial or mixed results easy to identify in the output.
OLD=$(printf 'o%.0s' $(seq 40)); A=$(printf 'A%.0s' $(seq 40)); B=$(printf 'B%.0s' $(seq 40))

# Put the original version in the shared file before any test client connects.
echo "$OLD" > "$EXPORT/f.txt"

# Create the first writer's script: replace f.txt with 40 A characters, then quit.
WA=$(mk wa.txt "write f.txt $A" quit)

# Create the second writer's script: replace f.txt with 40 B characters, then quit.
WB=$(mk wb.txt "write f.txt $B" quit)

# Create a reader script that waits locally for one second, reads f.txt, and quits.
# The local sleep lets the first delayed write be in progress when this client reads.
RD=$(mk rd.txt "sleep 1000" "read f.txt" quit)

# Announce which client writes or reads and when the reader is expected to arrive.
echo "== client 1 writes A's, client 2 writes B's, client 3 reads (arrives ~1 s in, mid-write) =="

# Start the two writers and then the delayed reader; the common helper briefly
# spaces launches so the server assigns client IDs in the expected order.
launch "$WA" "$WORK/o1"; launch "$WB" "$WORK/o2"; launch "$RD" "$WORK/o3"

# Wait for all clients to finish before examining logs and file contents.
wait_clients

# Print lock events for f.txt so writer serialization and reader timing are visible.
excerpt "path=/f.txt"

# Extract the content returned by the reader and read the final on-disk content.
got=$(read_result "$WORK/o3"); final=$(cat "$EXPORT/f.txt")

# Display both observed values so a person can inspect them as well as the checks.
echo "reader saw : $got"; echo "final file : $final"

# Define a valid complete file as the original contents or either writer's version.
whole() { [ "$1" = "$OLD" ] || [ "$1" = "$A" ] || [ "$1" = "$B" ]; }

# Confirm one writer's GET comes after the other writer's RELEASE, in either order.
no_overlap() {
  [ "$(lineno GET 2 /f.txt)" -gt "$(lineno RELEASE 1 /f.txt)" ] ||
  [ "$(lineno GET 1 /f.txt)" -gt "$(lineno RELEASE 2 /f.txt)" ]; }

# Report whether the log proves that the two writers never held the lock together.
pass_if "the two writers never overlap" no_overlap

# Report whether the reader received a complete version rather than partial/mixed data.
pass_if "reader saw one complete version (no mix)" whole "$got"

# Report whether the final file also matches one of the complete expected versions.
pass_if "final file is one complete version" whole "$final"
