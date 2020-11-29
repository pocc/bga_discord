#!/usr/bin/env bash
# Run the main script
.PHONY: run kill

kill:
	@kill `cat pid` 2>/dev/null || true
run: kill
	@python3 -u src/main.py 2>&1 >> errs & echo $$! > pid
