#!/usr/bin/env bash
# Experiment B: prove same-file writes serialize and readers cannot see a partial write.
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
start_server exp_b
# Use distinct repeated strings so a mixed or partial file is easy to recognize.
OLD=$(printf 'o%.0s' $(seq 40)); A=$(printf 'A%.0s' $(seq 40)); B=$(printf 'B%.0s' $(seq 40))
echo "$OLD" > "$EXPORT/f.txt"
# Start two writers and a reader that arrives during the first delayed write.
WA=$(mk wa.txt "write f.txt $A" quit); WB=$(mk wb.txt "write f.txt $B" quit)
RD=$(mk rd.txt "sleep 1000" "read f.txt" quit)
echo "== client 1 writes A's, client 2 writes B's, client 3 reads (arrives ~1 s in, mid-write) =="
launch "$WA" "$WORK/o1"; launch "$WB" "$WORK/o2"; launch "$RD" "$WORK/o3"
wait_clients
excerpt "path=/f.txt"
got=$(read_result "$WORK/o3"); final=$(cat "$EXPORT/f.txt")
echo "reader saw : $got"; echo "final file : $final"
# A valid result must match one complete version: original, first write, or second write.
whole() { [ "$1" = "$OLD" ] || [ "$1" = "$A" ] || [ "$1" = "$B" ]; }
# In the event log, the second writer must acquire only after the first releases.
no_overlap() {
  [ "$(lineno GET 2 /f.txt)" -gt "$(lineno RELEASE 1 /f.txt)" ] ||
  [ "$(lineno GET 1 /f.txt)" -gt "$(lineno RELEASE 2 /f.txt)" ]; }
pass_if "the two writers never overlap" no_overlap
pass_if "reader saw one complete version (no mix)" whole "$got"
pass_if "final file is one complete version" whole "$final"
