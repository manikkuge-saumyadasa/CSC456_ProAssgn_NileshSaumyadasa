# Experiment E: demonstrate reader preference and how it can delay a waiting writer.
# A later reader may join the active reader group before a queued writer acquires.

# Load the shared experiment setup and helper functions.
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# Start a temporary server and store its event log in experiments/logs/exp_e.log.
start_server exp_e

# Create the file that all three clients will access.
echo "data" > "$EXPORT/f.txt"

# Client 1 immediately reads f.txt, becoming the first active reader.
R=$(mk r1.txt "read f.txt" quit)

# Client 2 waits locally for 300 ms, then requests the exclusive write lock.
W=$(mk w.txt "sleep 300" "write f.txt NEW" quit)

# Client 3 waits locally for 800 ms, then requests a read lock after the writer
# has queued; reader preference should allow it to join the active readers.
R3=$(mk r3.txt "sleep 800" "read f.txt" quit)

# Explain the intended sequence: first reader, queued writer, then later reader.
echo "== client 1 reads at 0 s, client 2 (writer) arrives ~0.4 s, client 3 reads at ~1.0 s =="

# Launch each scripted client; common helper pauses briefly between starts so IDs
# match the event checks below (client 1 reader, client 2 writer, client 3 reader).
launch "$R" "$WORK/o1"; launch "$W" "$WORK/o2"; launch "$R3" "$WORK/o3"

# Wait until all three clients finish their lock operations and disconnect.
wait_clients

# Print all lock events for f.txt so the acquisition order can be inspected.
excerpt "path=/f.txt"

# Define a check that passes only if client 3's read GET precedes client 2's write GET.
overtook() { [ "$(lineno GET 3 /f.txt)" -lt "$(lineno GET 2 /f.txt)" ]; }

# Report whether the later reader acquired the lock before the waiting writer.
pass_if "late reader 3 got the lock BEFORE the waiting writer 2" overtook
