TEST_ARTIFACTS ?= /tmp/coverage

.PHONY: install dev_install static_type_check pylint style_check test

install:
	python3 -m pip install --upgrade pip setuptools
	python3 -m pip install -r requirements.txt

dev_install: install
	python3 -m pip install -r dev-requirements.txt

static_type_check:
	mypy media_downloader.py utils module --ignore-missing-imports

pylint:
	pylint media_downloader.py utils module -r y

style_check: static_type_check pylint

test:
	py.test --cov media_downloader --doctest-modules \
		--cov utils \
		--cov module/app.py \
		--cov-report term-missing \
		--cov-report html:${TEST_ARTIFACTS} \
		--junit-xml=${TEST_ARTIFACTS}/media-downloader.xml \
		tests/
