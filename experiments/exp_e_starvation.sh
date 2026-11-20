#!/usr/bin/env bash
# Optional Experiment E: demonstrate how reader preference can keep a waiting writer back.
# A reader that arrives AFTER the waiting writer still joins the active readers
# (reader preference), so the writer is pushed back again.
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
start_server exp_e
echo "data" > "$EXPORT/f.txt"
# The first reader holds the lock, the writer queues, then another reader arrives.
R=$(mk r1.txt "read f.txt" quit)
W=$(mk w.txt "sleep 300" "write f.txt NEW" quit)
R3=$(mk r3.txt "sleep 800" "read f.txt" quit)
echo "== client 1 reads at 0 s, client 2 (writer) arrives ~0.4 s, client 3 reads at ~1.0 s =="
launch "$R" "$WORK/o1"; launch "$W" "$WORK/o2"; launch "$R3" "$WORK/o3"
wait_clients
excerpt "path=/f.txt"
# Reader 3 should acquire before writer 2, showing that the lock favors readers.
overtook() { [ "$(lineno GET 3 /f.txt)" -lt "$(lineno GET 2 /f.txt)" ]; }
pass_if "late reader 3 got the lock BEFORE the waiting writer 2" overtook
