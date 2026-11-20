# Experiment C: verify that a lock on one file does not block another file.

# Load common setup and helper functions for this experiment.
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# Start a temporary server and save its events in experiments/logs/exp_c.log.
start_server exp_c

# Create y.txt so the second client's read has a valid target.
echo "yyy" > "$EXPORT/y.txt"

# Client 1 writes x.txt and holds its file lock during the configured server delay.
W=$(mk w.txt "write x.txt XXXX" quit)

# Client 2 waits locally for 500 ms, then reads y.txt while client 1 is writing.
R=$(mk r.txt "sleep 500" "read y.txt" quit)

# Explain the planned overlap, including which path each client uses.
echo "== client 1 writes /x.txt (holds its lock ${DELAY} ms); client 2 reads /y.txt at ~0.5 s =="

# Launch the writer, then the reader with the common helper's short spacing.
launch "$W" "$WORK/o1"; launch "$R" "$WORK/o2"

# Wait for both clients to finish before checking their lock activity.
wait_clients

# Show WAIT/GET/RELEASE events for both x.txt and y.txt side by side in time.
excerpt "path=/(x|y).txt"

# Measure how long client 2 spent between requesting and getting y.txt's read lock.
ms=$(waitms 2 /y.txt)

# Display the measured wait so it can be compared with expected lock contention.
echo "client 2 waited ${ms} ms for /y.txt"

# Pass when the read lock for y.txt was acquired promptly despite the x.txt write.
pass_if "reader of y.txt was not blocked (< 100 ms)" [ "$ms" -lt 100 ]
