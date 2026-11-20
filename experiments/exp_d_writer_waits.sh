#!/usr/bin/env bash
# Experiment D: a writer must wait until every reader currently holding the file lock exits.
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
start_server exp_d
echo "data" > "$EXPORT/f.txt"
# Two clients begin reads; the writer starts after a short delay.
R=$(mk r.txt "read f.txt" quit); W=$(mk w.txt "sleep 500" "write f.txt NEW" quit)
echo "== clients 1,2 read /f.txt; client 3 (writer) arrives ~0.7 s later =="
launch "$R" "$WORK/o1"; launch "$R" "$WORK/o2"; launch "$W" "$WORK/o3"
wait_clients
excerpt "path=/f.txt"
echo "writer waited $(waitms 3 /f.txt) ms"
# Confirm the writer GET event appears after the RELEASE event from each reader.
after_both() {
  [ "$(lineno GET 3 /f.txt)" -gt "$(lineno RELEASE 1 /f.txt)" ] &&
  [ "$(lineno GET 3 /f.txt)" -gt "$(lineno RELEASE 2 /f.txt)" ]; }
pass_if "writer got the lock only after both readers released" after_both
