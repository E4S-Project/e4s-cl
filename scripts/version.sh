#!/bin/bash

# Plumbing to transform git tags and hashes into a format
# accessible by setuptools

version=$(git describe --tags 2> /dev/null || echo "v0.0.0")

if [ "$version" != "v0.0.0" ]; then
    #PEP 440 compliance
    version=$(echo "$version" | cut -d- -f1 | sed -e 's/-/./')
fi

echo $version
