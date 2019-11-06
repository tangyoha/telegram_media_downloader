TEST_ARTIFACTS ?= /tmp/coverage

.PHONY: install deps

deps: install
	pip install -r dev-requirements.txt

install:
	pip install --upgrade pip setuptools
	pip install -r requirements.txt 

static_type_check:
	mypy media_downloader.py --ignore-missing-imports

pylint:
	pylint media_downloader.py -r y

test:
	py.test --cov media_downloader --doctest-modules \
		--cov-report term-missing \
		--cov-report html:${TEST_ARTIFACTS} \
		--junit-xml=${TEST_ARTIFACTS}/media-downloader.xml \
		tests/ 