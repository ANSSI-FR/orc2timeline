# ----------------------------------------------------------------------
# OS dependent configuration
# ----------------------------------------------------------------------

VENV=venv/bin/
LIB=venv/Lib/site-packages/
MARKER=venv/marker
EXE=
ifeq ($(OS),Windows_NT)
VENV=venv/Scripts/
LIB=venv/Lib/site-packages/
MARKER=venv/marker
EXE=.exe
endif


# ----------------------------------------------------------------------
# Python interpreter detection
# ----------------------------------------------------------------------

ARG_COMMAND="import sys;print(sys.version_info[:2]>=(3, 8))"

ifeq (ok,$(shell test -e /dev/null 2>&1 && echo ok))
NULL_STDERR=2>/dev/null
else
NULL_STDERR=2>NUL
endif

ifndef PY

ifndef _PY
ifeq (True,$(shell py -3 -c $(ARG_COMMAND) $(NULL_STDERR)))
_PY=py -3
endif
endif

ifndef _PY
ifeq (True,$(shell python3 -c $(ARG_COMMAND) $(NULL_STDERR)))
_PY=python3
endif
endif

ifndef _PY
ifeq (True,$(shell python -c $(ARG_COMMAND) $(NULL_STDERR)))
PY=python
endif

endif

ifndef _PY
$(error Could not detect Python 3.8 or greather interpreter automatically, please use PY environment variable.)
endif

PY=$(shell $(_PY) -c "import os,sys;print(sys.base_prefix.replace(os.sep,'/') + ('/python.exe' if os.name == 'nt' else '/bin/python3'))")

endif

ifneq (True,$(shell $(PY) -c $(ARG_COMMAND) $(NULL_STDERR)))
$(error $(PY) is not a valid Python 3.8 or greather interpreter)
endif

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

GIT=git
PIP=$(PY) -m pip
VENV_PY=$(VENV)python$(EXE)
VENV_PIP=$(VENV)pip$(EXE)

RM_GLOB := $(PY) -c "import shutil,sys,pathlib;[shutil.rmtree(sp, ignore_errors=False) if sp.is_dir() else sp.unlink() for p in sys.argv[1:]for sp in pathlib.Path().resolve().glob(p)]"
BROWSER := $(PY) -c "import os,webbrowser,sys;from urllib.request import pathname2url;webbrowser.open('file:'+pathname2url(os.path.abspath(sys.argv[1])))"
EXTRACT_HELP := $(PY) -c "import re,sys;m=[re.match(r'^([a-zA-Z_-]+):.*?\#\# (.*)$$',line)for line in sys.stdin];print('\n'.join('{:14} {}'.format(*g.groups())for g in m if g))"
LS := $(PY) -c "import sys,os;print('\n'.join(os.listdir(os.path.abspath(sys.argv[1]))))"
TOUCH := $(PY) -c "import sys;open(sys.argv[1],'ab')"

TOX=$(VENV)tox$(EXE)
SPHINX=$(VENV)sphinx-build$(EXE)
COVERAGE=$(VENV)coverage$(EXE)
TWINE=$(VENV)twine$(EXE)


# ----------------------------------------------------------------------
# Automatic installation
# ----------------------------------------------------------------------

.git:
	$(GIT) init
	$(GIT) add *
	$(GIT) commit -m "Initial commit"
	$(GIT) branch -M main

$(MARKER):
	$(MAKE) clean
	$(MAKE) .git
	$(PIP) install virtualenv
	$(PY) -m virtualenv venv
	$(VENV_PIP) install 'setuptools>=62.0.0' 'pip>=21.3'
	$(VENV_PIP) install -e .[lint]

	$(TOUCH) $(MARKER)

$(VENV): $(MARKER)

$(VENV_PY): $(MARKER)

$(VENV_PIP): $(MARKER)

$(TOX): $(VENV_PIP)
	$(VENV_PIP) install -e .[tox]

$(PRECOMMIT): $(VENV_PIP)

$(COVERAGE): $(VENV_PIP)
	$(VENV_PIP) install -e .[cov]

$(TWINE): $(VENV_PIP)
	$(VENV_PIP) install -e .[deploy]

$(LIB)build: $(VENV_PIP)
	$(VENV_PIP) install -e .[build]


# ----------------------------------------------------------------------
# Commands
# ----------------------------------------------------------------------

.DEFAULT_GOAL := help

.PHONY: clean
clean:  ## Remove all build, test, coverage, venv and Python artifacts.
	$(RM_GLOB) 'venv/*/python.?e?x?e?' 'venv' 'build/' 'dist/' 'public/' '.eggs/' '.tox/' '.coverage' 'htmlcov/' '.pytest_cache' '.mypy_cache' '.ruff_cache'  '**/*.egg-info' '**/*.egg' '**/__pycache__' '**/*~' '**/*.pyc' '**/*.pyo'

.PHONY: cov
cov: $(TOX)  ## Check code coverage.
	tox -e cov

.PHONY: dist
dist: clean $(LIB)build  ## Builds source and wheel package.
	$(VENV_PY) -m build
	$(LS) dist/

.PHONY: format
format: $(TOX) ## Format style with tox, ruff, black.
	$(TOX) -e format

.PHONY: help
help:  ## Show current message.
	@$(EXTRACT_HELP) < $(MAKEFILE_LIST)

.PHONY: install
install:  ## Install the package to the active Python's site-packages.
	$(PIP) install .

.PHONY: lint
lint: $(TOX)  ## Check style with tox, ruff, black and mypy.
	$(TOX) -e lint

.PHONY: open-cov
open-cov: cov  ## Open coverage report.
	$(BROWSER) htmlcov/index.html

.PHONY: setup
setup: clean $(VENV_PY)  ## Create virtual environment.

.PHONY: tests
tests: $(TOX)  ## Run unit and functional tests.
	$(TOX) -e tests

.PHONY: tests-all
tests-all: $(TOX)  ## Run all tests in parallel (lint and tests).
	$(TOX) -p

.PHONY: uninstall
uninstall:  ## Install the package to the active Python's site-packages.
	$(PIP) uninstall orc2timeline
