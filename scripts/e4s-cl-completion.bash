#!/bin/bash

complete_profile() {
    if [ -z "$(which e4s-cl 2>/dev/null)" ]; then
        return 
    fi

    # <e4s-cl> profile <subcommand> PROFILE
    if [ "${COMP_WORDS[1]}" = "profile" -a "${#COMP_WORDS[@]}" = "4" ]; then
        COMPREPLY=($(compgen -W "$(e4s-cl profile list -s)" "${COMP_WORDS[3]}"))
        return
    fi

    index=$((${#COMP_WORDS[@]} - 1))
    COMPREPLY=($(compgen -W "$(E4S_COMPLETION=Y "${COMP_WORDS[@]:0:$index}" -h)" "${COMP_WORDS[$index]}"))
}

complete -F complete_profile e4s-cl
