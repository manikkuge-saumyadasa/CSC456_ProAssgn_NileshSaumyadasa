#!/usr/bin/env bash
# Experiment C: work on one file should not make a client wait for a different file.
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
start_server exp_c
echo "yyy" > "$EXPORT/y.txt"
# Client 1 writes x.txt; client 2 starts a delayed read of y.txt.
W=$(mk w.txt "write x.txt XXXX" quit); R=$(mk r.txt "sleep 500" "read y.txt" quit)
echo "== client 1 writes /x.txt (holds its lock ${DELAY} ms); client 2 reads /y.txt at ~0.5 s =="
launch "$W" "$WORK/o1"; launch "$R" "$WORK/o2"
wait_clients
excerpt "path=/(x|y).txt"
# Compare client 2's WAIT and GET events to measure time blocked on y.txt.
ms=$(waitms 2 /y.txt); echo "client 2 waited ${ms} ms for /y.txt"
pass_if "reader of y.txt was not blocked (< 100 ms)" [ "$ms" -lt 100 ]
