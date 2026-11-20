# Experiment D: verify that a writer waits until all active readers release a file.

# Load common server/client setup and the log-inspection helpers.
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# Start an isolated server and save its events in experiments/logs/exp_d.log.
start_server exp_d

# Create the file that the readers and writer will access.
echo "data" > "$EXPORT/f.txt"

# Create a reader script that reads f.txt and then disconnects.
R=$(mk r.txt "read f.txt" quit)

# Create a writer script that waits locally for 500 ms, writes NEW, then quits.
# The delay lets both readers acquire their shared locks before the writer arrives.
W=$(mk w.txt "sleep 500" "write f.txt NEW" quit)

# Describe the intended arrival order; the writer should encounter active readers.
echo "== clients 1,2 read /f.txt; client 3 (writer) arrives ~0.7 s later =="

# Launch two readers and then the delayed writer, keeping client IDs predictable.
launch "$R" "$WORK/o1"; launch "$R" "$WORK/o2"; launch "$W" "$WORK/o3"

# Wait for every client to finish before evaluating event ordering.
wait_clients

# Print this file's lock events to show readers' overlapping holds and the writer wait.
excerpt "path=/f.txt"

# Calculate and display how long client 3 waited between WAIT and GET for its write lock.
echo "writer waited $(waitms 3 /f.txt) ms"

# Verify that the writer acquired the lock after reader 1 released it and after
# reader 2 released it; both conditions must be true for this check to pass.
after_both() {
  [ "$(lineno GET 3 /f.txt)" -gt "$(lineno RELEASE 1 /f.txt)" ] &&
  [ "$(lineno GET 3 /f.txt)" -gt "$(lineno RELEASE 2 /f.txt)" ]; }

# Report whether both reader releases occurred before the writer's acquisition.
pass_if "writer got the lock only after both readers released" after_both
