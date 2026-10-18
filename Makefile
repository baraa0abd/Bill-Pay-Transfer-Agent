PYTHON ?= python
.PHONY: seed test eval heldout review run
seed:
	$(PYTHON) -m data.seed
test:
	$(PYTHON) -m pytest -q
eval:
	$(PYTHON) -m eval.run_eval
heldout:
	$(PYTHON) -m eval.run_eval --heldout
review:
	$(PYTHON) -m data.review_web
run:
	$(PYTHON) -m uvicorn app:app --host 127.0.0.1 --port 8000

