TEST_ARTIFACTS ?= /tmp/coverage

.PHONY: install deps

deps: install
	pip install -r dev-requirements.txt

install:
	pip install --upgrade pip setuptools
	pip install -r requirements.txt 
	pip install https://github.com/pyrogram/pyrogram/archive/asyncio.zip

static_type_check:
	mypy media_downloader.py utils --ignore-missing-imports

pylint:
	pylint media_downloader.py utils -r y

test:
	py.test --cov media_downloader --doctest-modules \
		--cov utils \
		--cov-report term-missing \
		--cov-report html:${TEST_ARTIFACTS} \
		--junit-xml=${TEST_ARTIFACTS}/media-downloader.xml \
		tests/ 