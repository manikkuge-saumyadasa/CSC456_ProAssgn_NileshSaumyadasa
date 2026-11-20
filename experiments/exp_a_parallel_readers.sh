# Experiment A: verify that several clients can read the same file at once.
# Each read holds its lock for DELAY milliseconds, so overlapping reads should
# take about one delay period total instead of three delay periods.

# Load the common functions for starting servers, launching clients, and checks.
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# Start an isolated server and write its lock events to experiments/logs/exp_a.log.
start_server exp_a

# Put a test file in the server's temporary exported directory.
echo "hello from big.txt" > "$EXPORT/big.txt"

# Create one command script that reads big.txt and then closes its client session.
R=$(mk reader.txt "read big.txt" "quit")

# Print the scenario and configured delay so the run output is self-explanatory.
echo "== clients 1-3 all read /big.txt (delay=${DELAY} ms) =="

# Record the start time before launching any readers.
t0=$(now)

# Launch three clients with the same read script; zero launch spacing makes them
# arrive close together and gives their shared read locks a chance to overlap.
launch "$R" "$WORK/o1" 0; launch "$R" "$WORK/o2" 0; launch "$R" "$WORK/o3" 0

# Wait until all three client processes finish, then record the elapsed end time.
wait_clients; t1=$(now)

# Print this file's WAIT, GET, and RELEASE events to show their lock timing.
excerpt "path=/big.txt"

# Subtract start from end and format the total wall-clock time to two decimals.
el=$(awk "BEGIN{printf \"%.2f\", $t1-$t0}")

# Compare the measured time with the expected serialized time (3 x DELAY).
echo "total wall time: $el s  (serialized it would be 3 x ${DELAY} ms)"

# Pass if the elapsed time is less than 1.5 delay periods; this allows some
# startup/scheduling overhead while distinguishing parallel from serial reads.
pass_if "finished in under 1.5 x delay" awk "BEGIN{exit !($el < 1.5*$DELAY/1000)}"
