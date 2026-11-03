.PHONY: help verify verify-python verify-go verify-rust verify-c verify-shell verify-sql extract

help:
	@echo "make verify            run every example and solution in every language"
	@echo "make verify-<lang>     python | go | rust | c | shell | sql"
	@echo "make extract LESSON=python/01-values.md [OUT=work] [SOLUTION=1]"

verify:
	python3 tools/verify.py

verify-python verify-go verify-rust verify-c verify-shell verify-sql:
	python3 tools/verify.py $(subst verify-,,$@)

OUT ?= work
extract:
	@test -n "$(LESSON)" || (echo "usage: make extract LESSON=python/01-values.md"; exit 2)
	python3 tools/extract.py $(LESSON) -o $(OUT) $(if $(SOLUTION),--solution)
