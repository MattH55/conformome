# Conformome pipeline. Every number on the site comes from these targets; nothing is hand-edited.
#   make download                      fetch raw inputs (network), write data/MANIFEST.json
#   make site                          ingest -> map -> models -> static site in site/dist/
#   make validate                      site + schema, reference, licence and link checks + tests
# Limit to some proteins with ACC="P69441 P0DP23".
PYTHON ?= python3
ACC ?=

.PHONY: download ingest map models site validate test clean paper

download:
	$(PYTHON) -m conformome download $(ACC)

ingest:
	$(PYTHON) -m conformome ingest $(ACC)

map: ingest
	$(PYTHON) -m conformome map $(ACC)

models: map
	$(PYTHON) -m conformome models $(ACC)

site: models
	$(PYTHON) -m conformome site $(ACC)

test:
	$(PYTHON) -m pytest -q

validate: site test
	$(PYTHON) -m conformome validate $(ACC)

clean:
	rm -rf build site/dist

paper:
	bash paper/build_formatted.sh
