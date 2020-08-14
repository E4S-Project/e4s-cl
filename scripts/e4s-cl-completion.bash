#!/bin/bash

complete_profile() {
    if [ -z "$(which e4s-cl 2>/dev/null)" ]; then
        return 
    fi

    if [ "${COMP_WORDS[1]}" != "profile" ]; then
        return
    fi

    # <e4s-cl> profile <subcommand> PROFILE
    if [ "${#COMP_WORDS[@]}" != "4" ]; then
        return
    fi

    COMPREPLY=($(compgen -W "$(e4s-cl profile list -s)" "${COMP_WORDS[3]}"))
}

complete -F complete_profile e4s-cl
