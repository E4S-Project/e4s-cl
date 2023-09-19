RM = rm -f
MV = mv -f
COPY = cp -rv
MKDIR = mkdir -p
RMDIR = rm -fr

VERSION = $(shell git describe --tags --abbrev=0 2>/dev/null || echo "0.0.0")

# Get build system locations from configuration file or command line
ifneq ("$(wildcard setup.cfg)","")
	INSTALLDIR = $(shell grep '^prefix =' setup.cfg | sed 's/prefix = //')
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
ifeq ($(HOST_OS),Linux)
	CONDA_OS = Linux
else
	USE_MINICONDA = false
endif
ifeq ($(HOST_ARCH),x86_64)
	CONDA_ARCH = x86_64
else
	ifeq ($(HOST_ARCH),ppc64le)
	CONDA_ARCH = ppc64le
else
	USE_MINICONDA = false
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

HOME_MARKER = .e4s-cl-home

all: install completion man

#>============================================================================<
# Conda setup and fetch target

$(CONDA): $(CONDA_SRC)
	@bash $< -b -u -p $(CONDA_DEST)
	@touch $(CONDA_BIN)/*
	@# The following libraries are RPATH'ed and outdated - preventing the use of ctype in python code. Remove them to use the system's.
	@rm $(CONDA_DEST)/lib/libcrypto*

$(CONDA_SRC):
	$(MKDIR) `dirname "$(CONDA_SRC)"`
	$(call download,$(CONDA_URL),$(CONDA_SRC)) || \
		(rm -f "$(CONDA_SRC)" ; \
		echo "* ERROR: Unable to download $(CONDA_URL)." ; \
		false)

#>============================================================================<
# Main installation target

install: $(PYTHON_EXE)
	$(PYTHON) -m pip install -q --compile .
	$(MKDIR) $(INSTALL_BIN_DIR)
	ln -fs $(CONDA_BIN)/e4s-cl $(INSTALL_BIN_DIR)/e4s-cl
	touch $(INSTALLDIR)/$(HOME_MARKER)

#>============================================================================<
# Data fetching targets

COMPLETION_TARGET=$(shell git describe --abbrev=0 --tags)
COMPLETION_BIN_URL=https://github.com/E4S-Project/e4s-cl/releases/download/$(COMPLETION_TARGET)/completion.$(HOST_ARCH)
COMPLETION_DEST=$(INSTALLDIR)/bin/__e4s_cl_completion.$(HOST_ARCH)

completion:
	$(MKDIR) $(INSTALL_BIN_DIR)
	$(call download,$(COMPLETION_BIN_URL),$(COMPLETION_DEST)) || \
		(rm -f "$(COMPLETION_DEST)" ; \
		echo "* ERROR: Unable to download $(COMPLETION_BIN_URL)." ; \
		false)
	chmod +x $(COMPLETION_DEST)
	$(MKDIR) $(COMPLETION_DIR)
	$(COMPLETION_DEST) > $(COMPLETION_DIR)/e4s-cl
	echo "Please source '$(COMPLETION_DIR)/e4s-cl' to enable completion to the current shell."
	echo "If the bash-completion package is installed, completion will be enabled on new sessions."

#>============================================================================<
# Documentation targets and variables

PROJECT=.
DOCS=$(PROJECT)/docs
MANBUILDDIR=$(PROJECT)/docs/build/man
USER_MAN=$(INSTALLDIR)/man

man: $(PYTHON_EXE)
	$(PYTHON) -m pip install -q -U -r ./docs/requirements.txt
	VERSION=$(VERSION) PATH=$(CONDA_BIN):$(PATH) $(MAKE) -C $(DOCS) man
	$(MKDIR) $(USER_MAN)/man1
	$(COPY) $(MANBUILDDIR)/* $(USER_MAN)/man1
	echo "Append '$(USER_MAN)' to your MANPATH to access the e4s-cl manual."

html: $(PYTHON_EXE)
	find $(DOCS) -exec touch {} \;
	$(PYTHON) -m pip install -q -U -r ./docs/requirements.txt
	VERSION=$(VERSION) PATH=$(CONDA_BIN):$(PATH) $(MAKE) -C $(DOCS) html

clean:
	rm -fr build/ COMMIT VERSION
