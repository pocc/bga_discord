#!/usr/bin/env bash
# Run the main script
.PHONY: run kill

kill:
	@kill `cat pid` 2>/dev/null || true
run: kill
	@python3 -u bga_discord.py 2>&1 & echo $$! > pid | tee -a errs 
