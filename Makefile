.PHONY: help verify verify-python verify-go verify-rust verify-c verify-shell verify-sql extract pg-up pg-down

help:
	@echo "make verify            run every example and solution in every language"
	@echo "make verify-<lang>     python | go | rust | c | shell | sql"
	@echo "make extract LESSON=python/01-values.md [OUT=work] [SOLUTION=1]"
	@echo "make pg-up             start the PostgreSQL 16 container byexample-pg"
	@echo "make pg-down           stop and remove byexample-pg"

# SQL lessons talk to this container. See tools/sqlrun.py.
pg-up:
	@docker start byexample-pg >/dev/null 2>&1 || \
		docker run -d --name byexample-pg \
			-e POSTGRES_USER=byexample \
			-e POSTGRES_PASSWORD=byexample \
			-p 127.0.0.1:5432:5432 \
			postgres:16
	@i=0; until docker exec byexample-pg pg_isready -U byexample >/dev/null 2>&1; do \
		i=$$((i+1)); \
		if [ $$i -gt 60 ]; then echo "byexample-pg did not become ready"; exit 1; fi; \
		sleep 0.5; \
	done

pg-down:
	docker rm -f byexample-pg

verify:
	python3 tools/verify.py

verify-python verify-go verify-rust verify-c verify-shell verify-sql:
	python3 tools/verify.py $(subst verify-,,$@)

OUT ?= work
extract:
	@test -n "$(LESSON)" || (echo "usage: make extract LESSON=python/01-values.md"; exit 2)
	python3 tools/extract.py $(LESSON) -o $(OUT) $(if $(SOLUTION),--solution)
