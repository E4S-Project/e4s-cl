Completion script for [`e4s-cl`](https://github.com/E4S-Project/e4s-cl)
-------------------------------------

This repository is used to compile binaries shipped with `e4s-cl`. 

### Compilation

The file `src/completion.json` must contain a JSON file with all possible choices in the cli. A script in `e4s-cl/scripts/completion-json.py` allows to generate this file from an installed `e4s-cl` package. Then good practice is to build and strip:

```
cargo build --release
strip target/release/__e4s_cl_comp
```

### Usage

When called in a blank context, the binary should return the complete command it should be used with:

```
$ ./target/release/__e4s_cl_comp 
complete -C ./target/release/__e4s_cl_comp \
    -o bashdefault \
    -o default \
    -o filenames \
    e4s-cl
```

If called within a completion context, the `COMP_LINE` environment variable is studied to provide a list of available completions.


### Why rust ?

The first completion script for `e4s-cl` was written in python. This beast was slow, and loading the entire module to get a summary of available options was nowhere as efficient as expected from a completion script.
Rust allowed a convenient way to build and maintain a JSON-parser. The resulting binaries are almost static and portable, allowing them to be downloaded and run immediately.
