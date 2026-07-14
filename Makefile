.PHONY: install run test smoke

install:
	python -m pip install -r requirements.txt

run:
	python -m streamlit run app.py

test:
	python -m pytest -q

smoke:
	python scripts/smoke_test.py
