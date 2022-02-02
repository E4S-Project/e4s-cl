RM = rm -f
MV = mv -f
COPY = cp -rv
MKDIR = mkdir -p
RMDIR = rm -fr

VERSION = $(shell cat VERSION 2>/dev/null || $(shell pwd)/scripts/version.sh 2>/dev/null || echo "0.0.0")

# Get build system locations from configuration file or command line
ifneq ("$(wildcard setup.cfg)","")
	BUILDDIR = $(shell grep '^build-base =' setup.cfg | sed 's/build-base = //')
	INSTALLDIR = $(shell grep '^prefix =' setup.cfg | sed 's/prefix = //')
endif
ifeq ($(BUILDDIR),)
	BUILDDIR=build
endif
ifeq ($(INSTALLDIR),)
	INSTALLDIR=$(shell pwd)/e4s-cl-$(VERSION)
endif
INSTALL_BIN_DIR=$(INSTALLDIR)/bin

# Get target OS and architecture
ifeq ($(HOST_OS),)
	HOST_OS = $(shell uname -s)
endif
ifeq ($(HOST_ARCH),)
	HOST_ARCH = $(shell uname -m)
endif

WGET = $(shell command -pv wget || which wget)
CURL = $(shell command -pv curl || which curl)

ifneq ($(WGET),)
download = $(WGET) --no-check-certificate $(WGET_FLAGS) -O "$(2)" "$(1)"
else
ifneq ($(CURL),)
download = $(CURL) --insecure $(CURL_FLAGS) -L "$(1)" > "$(2)"
else
$(error Either curl or wget must be in PATH to download the python interpreter)
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
CONDA_REPO = https://repo.anaconda.com/miniconda
CONDA_PKG = Miniconda3-$(CONDA_VERSION)-$(CONDA_OS)-$(CONDA_ARCH).sh
CONDA_URL = $(CONDA_REPO)/$(CONDA_PKG)
CONDA_SRC = system/src/$(CONDA_PKG)
CONDA_DEST = $(INSTALLDIR)/conda
CONDA_BIN = $(CONDA_DEST)/bin
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

# Completion folder resolution from https://github.com/scop/bash-completion#faq
ifeq ($(BASH_COMPLETION_USER_DIR),)
	ifeq ($(XDG_DATA_HOME),)
		COMPLETION_DIR = $(HOME)/.local/share/bash-completion/completions
	else
		COMPLETION_DIR = $(XDG_DATA_HOME)/bash-completion/completions
	endif
else
	COMPLETION_DIR = $(BASH_COMPLETION_USER_DIR)/completions
endif

all: install completion man

#>============================================================================<
# Conda setup and fetch target

python_check: $(PYTHON_EXE)
	@$(PYTHON) -c "import sys; import setuptools;" || (echo "ERROR: setuptools is required." && false)
	$(PYTHON) -m pip install -q -U -r requirements.txt

python_download: $(CONDA_SRC)

$(CONDA): $(CONDA_SRC)
	bash $< -b -u -p $(CONDA_DEST)
	touch $(CONDA_BIN)/*

$(CONDA_SRC):
	$(MKDIR) `dirname "$(CONDA_SRC)"`
	@$(call download,$(CONDA_URL),$(CONDA_SRC)) || \
		(rm -f "$(CONDA_SRC)" ; \
		echo "* ERROR: Unable to download $(CONDA_URL)." ; \
		false)

#>============================================================================<
# Main installation target

install: python_check download_assets
	$(PYTHON) setup.py build -b "$(BUILDDIR)"
	$(PYTHON) setup.py build_scripts --executable "$(PYTHON)"
	$(PYTHON) setup.py install --prefix $(INSTALLDIR) --force
	@$(PYTHON) scripts/success.py "Installation succeded. Please add '$(INSTALLDIR)/bin' to your PATH."

#>============================================================================<
# Data fetching targets

ASSET_URL=https://oaciss.uoregon.edu/e4s/e4s-cl

download_assets: python_check
	$(PYTHON) scripts/download_assets.py $(ASSET_URL) $(HOST_ARCH) $(SYSTEM)

COMPLETION_TARGET=$(shell git describe --abbrev=0 --tags)
COMPLETION_BIN_URL=https://github.com/E4S-Project/e4s-cl/releases/download/$(COMPLETION_TARGET)/completion.$(HOST_ARCH)
COMPLETION_DEST=$(INSTALLDIR)/bin/__e4s_cl_completion.$(HOST_ARCH)

completion:
	@$(MKDIR) $(INSTALL_BIN_DIR)
	@$(call download,$(COMPLETION_BIN_URL),$(COMPLETION_DEST)) || \
		(rm -f "$(COMPLETION_DEST)" ; \
		echo "* ERROR: Unable to download $(COMPLETION_BIN_URL)." ; \
		false)
	@chmod +x $(COMPLETION_DEST)
	@$(MKDIR) $(COMPLETION_DIR)
	@$(COMPLETION_DEST) > $(COMPLETION_DIR)/e4s-cl
	@$(PYTHON) scripts/success.py "Please source '$(COMPLETION_DIR)/e4s-cl' to enable completion to the current shell."
	@$(PYTHON) scripts/success.py "If the bash-completion package is installed, completion will be enabled on new sessions."

#>============================================================================<
# Documentation targets and variables

PROJECT=.
DOCS=$(PROJECT)/docs
MAN=$(PROJECT)/docs/build/man
USER_MAN=$(HOME)/.local/share/man

man: python_check
	$(PYTHON) -m pip install -q -U -r $(DOCS)/requirements.txt
	VERSION=$(VERSION) PATH=$(CONDA_BIN):$(PATH) $(MAKE) -C $(DOCS) man
	@$(MKDIR) $(USER_MAN)/man1
	@$(COPY) $(MAN)/* $(USER_MAN)/man1
	@MANPATH=$(MANPATH):$(USER_MAN) mandb || true
	@$(PYTHON) scripts/success.py "Append '$(USER_MAN)' to your MANPATH to access the e4s-cl manual."


clean:
	rm -fr build/ COMMIT VERSION

#>============================================================================<
# Maintenance targets

ifneq ($(TEST_ENV),)
TEST_ENV = deep_test
TEST_DEPENDENCIES = install python_check
else
TEST_ENV = shallow_test
TEST_DEPENDENCIES =
endif

__E4S_CL_USER_PREFIX__ = /tmp/$(USER)/e4s_cl/user_test
__E4S_CL_SYSTEM_PREFIX__ = /tmp/$(USER)/e4s_cl/system_test

test: $(TEST_DEPENDENCIES)
	$(PYTHON) -m tox tox.ini -e $(TEST_ENV)

format:
	bash ./scripts/format.sh packages/e4s_cl

ifeq ($(LINT_FILE),)
LINT_FILE=packages/e4s_cl
endif

lint:
	@$(PYTHON) -m pip install pylint
	$(PYTHON) -m pylint --rcfile pylintrc --output-format=colorized -r n $(LINT_FILE)

#>============================================================================<
