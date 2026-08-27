PYTHON ?= python

.PHONY: assurance compile lint test verify-snapshot verify-repository verify-manifest live

assurance:
	bash scripts/run_research_assurance.sh

compile:
	$(PYTHON) -m py_compile $$(cat config/canonical_scripts.txt)

lint:
	$(PYTHON) -m ruff check $$(cat config/canonical_scripts.txt) tests tests_public scripts

test:
	$(PYTHON) -m pytest -q tests tests_public

verify-snapshot:
	$(PYTHON) scripts/verify_research_snapshot.py

verify-repository:
	$(PYTHON) scripts/research/verify_repository.py

verify-manifest:
	$(PYTHON) scripts/build_publication_manifest.py --verify

live:
	bash scripts/reproduce_live.sh
