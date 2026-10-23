PYTHON ?= python

.PHONY: data train eval test app report

data:
	$(PYTHON) -m src.data.generate_corpus

train:
	$(PYTHON) -m src.models.train

eval:
	$(PYTHON) -m src.models.eval

test:
	$(PYTHON) -m pytest -q

app:
	$(PYTHON) -m flask --app app:create_app run --debug

report:
	$(PYTHON) -m src.eval.external --help
