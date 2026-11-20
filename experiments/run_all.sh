# Run the concurrency demonstrations in order; each script starts and stops its own server.
# Logs are saved under experiments/logs/.
cd "$(dirname "${BASH_SOURCE[0]}")"
for s in exp_a_parallel_readers exp_b_writers exp_c_different_files exp_d_writer_waits exp_e_starvation; do
  echo; echo "################ $s ################"; bash "$s.sh"
done
