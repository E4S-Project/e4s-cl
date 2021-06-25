#!/bin/bash

# Plumbing to transform git tags and hashes into a format
# accessible by setuptools

VERSION_FILE=VERSION
COMMIT_FILE=COMMIT

version=$(git describe --tags 2> /dev/null || echo "v0.0.0")
commit=$(git rev-parse --short HEAD || echo "Unknown")

if [ "$version" != "v0.0.0" ]; then
    #PEP 440 compliance
    version=$(echo "$version" | cut -d- -f1 | sed -e 's/-/./')
fi

echo $commit > $COMMIT_FILE
echo "${version:1}" | tee $VERSION_FILE
