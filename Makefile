install:
	python3 -m venv venv
	venv/bin/pip install -U pip setuptools wheel
	venv/bin/pip install -r requirements.txt

format:
	venv/bin/ruff format .
