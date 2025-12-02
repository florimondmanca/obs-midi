install:
	python3 -m venv venv
	venv/bin/pip install -U pip setuptools wheel
	venv/bin/pip install -r requirements.txt

format:
	venv/bin/ruff format .

list:
	venv/bin/python main.py list

run:
	venv/bin/python main.py run -p 20:0 --obs-port 4455 --obs-password alternatepopper14
