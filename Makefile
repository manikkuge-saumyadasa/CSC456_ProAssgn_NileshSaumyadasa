# Run the provided scripts.
# `make part1` :- Run a set of file commands and expected error cases and write the output to `tests/part1_output.txt`.
# `make experiments` :- Run the readers-writers concurrency demonstrations and write the output to `tests/part1_server.log`.
# `make clean` :- Remove cache, generated output files, and logs.
.PHONY: part1 experiments clean

# Exercise the file commands and expected error cases.
part1:
	bash tests/run_part1.sh

# Run the readers-writers concurrency demonstrations.
experiments:
	bash experiments/run_all.sh

# Run both the file commands and the readers-writers concurrency demonstrations.
runall:
	bash tests/run_part1.sh
	bash experiments/run_all.sh 


# Remove Python cache and generated Part 1 output files.
clean:
	rm -rf src/__pycache__ tests/part1_output.txt tests/part1_server.log experiments/logs
