#!/bin/bash

FORMATTER=yapf
SRC="$1"
BUFFER=`mktemp`

function __hash() {
    cat "$1" | md5sum - | cut -f1 -d' '
}

if [ ! $(which "$FORMATTER") ] ; then
    echo "$FORMATTER not available !" >& 2
fi

LIST="$(find "$SRC" -name "*py")"

for file in $LIST; do
    echo -ne "\r$file "
    cat "$file" | "$FORMATTER" > "$BUFFER" 

    if [ ! $(__hash "$file") = $(__hash "$BUFFER") ] ; then
        echo has been formatted !
        cp "$BUFFER" "$file"
    else
        echo OK
    fi
done
