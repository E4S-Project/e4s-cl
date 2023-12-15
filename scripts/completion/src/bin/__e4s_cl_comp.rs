use dirs::home_dir;
use e4s_cl_completion::{Command, Profile};
use log::debug;
use shlex::split;
use simplelog::{Config, LevelFilter, WriteLogger};
use std::env;
use std::error::Error;
use std::fmt;
use std::fs::{canonicalize, File};
use std::io::BufReader;
use std::path::Path;
use std::process::exit;

static ENV_LINE_VAR: &str = "COMP_LINE";
static DATABASE: &'static str = ".local/e4s_cl/user.json";

#[derive(Debug)]
struct DeserializationError();

impl fmt::Display for DeserializationError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "Deserialization failed")
    }
}

impl Error for DeserializationError {}

fn load_profiles<P: AsRef<Path>>(path: P) -> Result<Vec<Profile>, Box<dyn Error>> {
    // Open the file in read-only mode with buffer.
    let file = File::open(path)?;
    let reader = BufReader::new(file);

    // Read the JSON contents of the file.
    let data: serde_json::Value = serde_json::from_reader(reader)?;

    match data["Profile"].as_object() {
        Some(map) => Ok(map
            .iter()
            .map(|(_i, data)| serde_json::from_value::<Profile>(data.to_owned()).unwrap())
            .collect()),
        None => Err(Box::new(DeserializationError())),
    }
}

fn load_commands() -> Result<Command, Box<dyn Error>> {
    Ok(serde_json::from_str(include_str!("completion.json"))?)
}

/// For a given command, delimit the arguments it consumes from the arguments slice
fn context_end(command: &Command, arguments: &[String]) -> usize {
    let mut iter = arguments.iter();
    debug!("Context for {:?}", arguments);

    while let Some(value) = iter.next() {
        if let Some(option) = command.is_option(value) {
            option.consume_args(command, &mut iter);
        }

        if let Some(_) = command.is_subcommand(value) {
            break;
        }
    }

    let (remaining, _) = iter.size_hint();
    arguments.len() - remaining - 1
}

/// Interpret arguments (the contents of the command line) with the available tokens (children of root and
/// profiles) and print a list of matching completion targets to the command line
fn routine(
    arguments: &Vec<String>,
    root: &Command,
    profiles: &Vec<Profile>,
) -> Result<(), Box<dyn Error>> {
    let mut pos = 0;
    let mut context_path: Vec<(&Command, usize)> = vec![(&root, 0)];

    while pos < arguments.len() {
        let token = &arguments[pos];

        // Disregard empty tokens
        if token.len() == 0 {
            pos += 1;
            continue;
        }

        let (context, _) = context_path.last().unwrap();
        let skip = context_end(context, &arguments[pos..]);
        debug!("Context: {:?} (skip {:?})", context.name, skip);

        if skip > 0 {
            pos += skip;

            let token = &arguments[pos];
            debug!("Next token: {:?}", token);
            match context.is_subcommand(token) {
                Some(command) => context_path.push((command, pos)),
                None => break,
            };
        } else {
            break;
        }
    }

    let (last_context, position) = context_path.last().unwrap();

    let last_token = arguments.last().unwrap();
    let candidates: Vec<String> = last_context
        .candidates(&arguments[*position..], &profiles)
        .iter()
        .cloned()
        .filter(|c| !c.starts_with("__"))
        .filter(|c| c.starts_with(last_token))
        .collect();

    debug!("Completion candidates: {:#?}", candidates);
    // Print all the candidates matching the start of the last token
    for completion in candidates.iter() {
        println!("{}", completion);
    }

    Ok(())
}

fn main() -> Result<(), Box<dyn Error>> {
    let mut args = env::args();
    let mut command_line: Vec<String>;

    if cfg!(debug_assertions) {
        WriteLogger::init(
            LevelFilter::Debug,
            Config::default(),
            File::create("/tmp/e4s-cl-completion.log").unwrap(),
        )
        .unwrap();
        debug!("Initialized logging #################################");
    }

    // Get the completion line from the environment
    let raw_cli = std::env::var(&ENV_LINE_VAR);
    if raw_cli.is_err() {
        let script = canonicalize(args.next().unwrap())?;
        print!(
            include_str!("complete.fmt"),
            script.to_str().unwrap(),
            script.to_str().unwrap()
        );
        exit(0);
    }

    let string = raw_cli.unwrap();

    // Chop it into parts, to understand what has already been written
    command_line = split(&string).ok_or("Command line split failed !")?;

    // Add a final element if finished by a space
    if string.chars().last().unwrap() == ' ' {
        command_line.push("".to_string())
    }

    debug!("Command line: {:?}", command_line);

    let root_command: Command = load_commands()?;
    let db_file = home_dir().unwrap().join(DATABASE);
    let profiles: Vec<Profile> = load_profiles(db_file)?;

    routine(&command_line, &root_command, &profiles)
}
