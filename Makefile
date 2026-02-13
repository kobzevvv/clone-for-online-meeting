.PHONY: install run dev eval test web clean

install:
	pip install -r requirements.txt

run:
	python main.py --mode voice

dev:
	python main.py --mode text

eval:
	python -m eval.run

test:
	pytest tests/ -v

web:
	python main.py --mode web

telegram:
	python main.py --mode telegram

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type f -name "*.pyc" -delete 2>/dev/null; true
