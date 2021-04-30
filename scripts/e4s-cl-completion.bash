#!/bin/bash

complete_profile() {
    # Toggle completion help
    export E4S_COMPLETION=Y

    __complete_profile $@

    # Disable special help formatting
    unset E4S_COMPLETION
}

__complete_profile() {
    # if e4s-cl is not in the path, do nothing
    if [ -z "$(which e4s-cl 2>/dev/null)" ]; then
        return 
    fi

    # Complete profile names in special cases
    # <e4s-cl> profile <subcommand> PROFILE
    if [ "${COMP_WORDS[1]}" = "profile" ]; then
        subaction="${COMP_WORDS[2]}"

        if [ "$subaction" = "create" -o "$subaction" = "detect" ]; then
            return
        fi

        if [ "$subaction" = "delete" -o "${#COMP_WORDS[@]}" = "4" ]; then
            COMPREPLY=($(compgen -W "$(e4s-cl profile list -s)" "${COMP_WORDS[-1]}"))
            return
        fi
    fi

    # Get the minimal command line and invoke -h on it
    minimal_index=$((${#COMP_WORDS[@]} - 1))
    paths="$( "${COMP_WORDS[@]:0:$minimal_index}" -h 2>/dev/null)"

    if [ "${#paths[@]}" = "0" ]; then
        return
    fi

    COMPREPLY=($(compgen -W "$paths" "${COMP_WORDS[$minimal_index]}"))
}

complete -F complete_profile -o default e4s-cl
