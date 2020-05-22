#!/usr/bin/env bash
# Run the main script
.PHONY: run clean

clean:
	@printf "" > errs
run: clean
	@python3 -u bga_discord.py 2>&1 | tee errs &
