ifneq (,$(wildcard ./.env))
	include .env
	export
endif

.SILENT: input_ports run

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

input_ports:
	venv/bin/python -c "import mido; print(*mido.get_input_names(), sep='\n')"

run:
	venv/bin/python -m obs_midi.gui ${ARGS}

dist:
	venv/bin/python -m obs_midi.packaging.build

clean:
	rm -r dist
