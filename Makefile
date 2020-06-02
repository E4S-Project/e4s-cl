RM = rm -f
MV = mv -f
MKDIR = mkdir -p

VERSION = $(shell cat VERSION 2>/dev/null || ./.version.sh 2>/dev/null || echo "0.0.0")

# Get build system locations from configuration file or command line
ifneq ("$(wildcard setup.cfg)","")
	BUILDDIR = $(shell grep '^build-base =' setup.cfg | sed 's/build-base = //')
	INSTALLDIR = $(shell grep '^prefix =' setup.cfg | sed 's/prefix = //')
endif
ifeq ($(BUILDDIR),)
	BUILDDIR=build
endif
ifeq ($(INSTALLDIR),)
	INSTALLDIR=$(HOME)/e4s-cl-$(VERSION)
endif

# Get target OS and architecture
ifeq ($(HOST_OS),)
	HOST_OS = $(shell uname -s)
endif
ifeq ($(HOST_ARCH),)
	HOST_ARCH = $(shell uname -m)
endif

WGET = $(shell command -pv wget || type -P wget || which wget)
ifneq ($(WGET),)
	download = $(WGET) --no-check-certificate $(WGET_FLAGS) -O "$(2)" "$(1)"
else
	CURL = $(shell command -pv curl || type -P curl || which curl)
	ifneq ($(CURL),)
		download = $(CURL) --insecure $(CURL_FLAGS) -L "$(1)" > "$(2)"
	else
		$(warning Either curl or wget must be in PATH to download packages)
	endif
endif

# Miniconda configuration
USE_MINICONDA = true
ifeq ($(HOST_OS),Darwin)
ifeq ($(HOST_ARCH),i386)
	USE_MINICONDA = false
endif
endif
ifeq ($(HOST_OS),Darwin)
	CONDA_OS = MacOSX
else
	ifeq ($(HOST_OS),Linux)
		CONDA_OS = Linux
	else
		USE_MINICONDA = false
	endif
endif
ifeq ($(HOST_ARCH),x86_64)
	CONDA_ARCH = x86_64
else
	ifeq ($(HOST_ARCH),i386)
		CONDA_ARCH = x86
	else
		ifeq ($(HOST_ARCH),ppc64le)
			CONDA_ARCH = ppc64le
		else
			USE_MINICONDA = false
		endif
	endif
endif

CONDA_VERSION = latest
CONDA_REPO = https://repo.continuum.io/miniconda
CONDA_PKG = Miniconda3-$(CONDA_VERSION)-$(CONDA_OS)-$(CONDA_ARCH).sh
CONDA_URL = $(CONDA_REPO)/$(CONDA_PKG)
CONDA_SRC = system/src/$(CONDA_PKG)
CONDA_DEST = $(INSTALLDIR)/conda
CONDA = $(CONDA_DEST)/bin/python

ifeq ($(USE_MINICONDA),true)
	PYTHON_EXE = $(CONDA)
	PYTHON_FLAGS = -EOu
else
	$(warning WARNING: There are no miniconda packages for this system: $(HOST_OS), $(HOST_ARCH).)
	CONDA_SRC =
	PYTHON_EXE = $(shell command -pv python || type -P python || which python)
	PYTHON_FLAGS = -O
	ifeq ($(PYTHON_EXE),)
		$(error python not found in PATH.)
	else
		$(warning WARNING: Trying to use '$(PYTHON_EXE)' instead.)
	endif
endif
PYTHON = $(PYTHON_EXE) $(PYTHON_FLAGS)

build: python_check
	$(PYTHON) -m pip install -U -r requirements.txt
	$(PYTHON) setup.py build_scripts --executable "$(PYTHON)"
	$(PYTHON) setup.py build

install: build
	$(PYTHON) setup.py install --prefix $(INSTALLDIR) --force

python_check: $(PYTHON_EXE)
	@$(PYTHON) -c "import sys; import setuptools;" || (echo "ERROR: setuptools is required." && false)

python_download: $(CONDA_SRC)

$(CONDA): $(CONDA_SRC)
	bash $< -b -u -p $(CONDA_DEST)
	touch $(CONDA_DEST)/bin/*

$(CONDA_SRC):
	$(MKDIR) `dirname "$(CONDA_SRC)"`
	@$(call download,$(CONDA_URL),$(CONDA_SRC)) || \
		(rm -f "$(CONDA_SRC)" ; \
		echo "* ERROR: Unable to download $(CONDA_URL)." ; \
		false)

clean:
	rm -fr build/

test: build
	$(PYTHON) -m tox tox.ini
