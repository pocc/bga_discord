#!/usr/bin/env bash
# Run the main script
.PHONY: run clean

clean:
	@printf "" > errs
run: clean
	@python3 bga_discord.py >errs 2>&1
