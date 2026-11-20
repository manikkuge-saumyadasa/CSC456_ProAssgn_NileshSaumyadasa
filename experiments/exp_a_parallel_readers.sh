#!/usr/bin/env bash
# Experiment A: show three clients sharing one file lock as readers.
# With a 2-second server delay, their reads should overlap and finish in about 2 seconds.
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
# Create a fresh server/export and save its event log as exp_a.log.
start_server exp_a
echo "hello from big.txt" > "$EXPORT/big.txt"
# Every client runs the same two commands: read the file, then disconnect.
R=$(mk reader.txt "read big.txt" "quit")
echo "== clients 1-3 all read /big.txt (delay=${DELAY} ms) =="
# Measure elapsed wall time to distinguish concurrent reads from serialized reads.
t0=$(now)
launch "$R" "$WORK/o1" 0; launch "$R" "$WORK/o2" 0; launch "$R" "$WORK/o3" 0
wait_clients; t1=$(now)
excerpt "path=/big.txt"
el=$(awk "BEGIN{printf \"%.2f\", $t1-$t0}")
echo "total wall time: $el s  (serialized it would be 3 x ${DELAY} ms = 6 s)"
pass_if "finished in under 1.5 x delay" awk "BEGIN{exit !($el < 1.5*$DELAY/1000)}"
