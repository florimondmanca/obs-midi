ifneq (,$(wildcard ./.env))
	include .env
	export
endif

.PHONY: dist

all: install dist

install:
	python3 -m venv venv
	venv/bin/pip install -U pip wheel
	venv/bin/pip install -r requirements.txt

install_dev:
	venv/bin/pip install -r requirements-dev.txt

check:
	venv/bin/ruff check --select I

format:
	venv/bin/ruff check --select I --fix
	venv/bin/ruff format

run:
	venv/bin/python -m obs_midi.gui ${ARGS}

dist:
	venv/bin/python -m obs_midi.packaging.build

clean:
	rm -r dist
