mod completable;
mod deserializers;

use completable::Completable;
use deserializers::{argument_count_de, expected_type_de};
use log::debug;
use serde::Deserialize;
use std::collections::HashMap;
use std::convert::TryInto;

#[derive(Deserialize, Debug)]
pub struct Profile {
    pub name: String,
}

#[derive(Deserialize, Debug, PartialEq, Eq, Hash)]
#[serde(untagged)]
pub enum ArgumentCount {
    Fixed(u64),
    AtMostOne(),
    AtLeastOne(),
    Any(),
}

#[derive(Deserialize, Debug, PartialEq, Eq, Hash)]
#[serde(untagged)]
pub enum ExpectedType {
    Unknown(),
    Profile(),
    Path(),
}

#[derive(Deserialize, Debug)]
pub struct Positional {
    #[serde(default)]
    #[serde(deserialize_with = "argument_count_de")]
    pub arguments: ArgumentCount,

    #[serde(default)]
    #[serde(deserialize_with = "expected_type_de")]
    pub expected_type: ExpectedType,
}

#[derive(Deserialize, Debug, PartialEq, Eq, Hash)]
pub struct Option_ {
    pub names: Vec<String>,

    #[serde(default)]
    pub values: Vec<String>,

    #[serde(default)]
    #[serde(deserialize_with = "argument_count_de")]
    pub arguments: ArgumentCount,

    #[serde(default)]
    #[serde(deserialize_with = "expected_type_de")]
    pub expected_type: ExpectedType,
}

#[derive(Deserialize, Debug)]
pub struct Command {
    pub name: String,

    #[serde(default)]
    pub subcommands: Vec<Command>,

    #[serde(default)]
    pub positionals: Vec<Positional>,

    #[serde(default)]
    pub options: Vec<Option_>,
}

impl Default for ArgumentCount {
    fn default() -> ArgumentCount {
        return ArgumentCount::Fixed(0);
    }
}

impl Default for ExpectedType {
    fn default() -> ExpectedType {
        return ExpectedType::Unknown();
    }
}

impl Option_ {
    pub fn complete<'a, T>(&self, command_line: &T) -> bool
    where
        T: Iterator<Item = &'a String> + std::fmt::Debug + Clone,
    {
        let mut command_line = (*command_line).clone();

        match self.arguments {
            ArgumentCount::Fixed(size) => {
                for _ in 0..size {
                    if let Some(value) = command_line.next() {
                        if value.as_str() == "" {
                            return false;
                        }
                    }
                }
                true
            }
            ArgumentCount::AtMostOne() => true,
            _ => true,
        }
    }

    pub fn consume_args<'a, T>(&self, parent: &Command, command_line: &mut T) -> Vec<String>
    where
        T: Iterator<Item = &'a String> + std::fmt::Debug,
    {
        let mut command_line = command_line.peekable();
        let mut args: Vec<String> = vec![];

        match self.arguments {
            ArgumentCount::Fixed(size) => {
                for _ in 0..size {
                    if let Some(value) = command_line.peek() {
                        if value.as_str() != "" {
                            args.push(command_line.next().unwrap().clone());
                        }
                    }
                }
            }

            ArgumentCount::AtMostOne() => {
                if let Some(value) = command_line.peek() {
                    if parent.is_option(&value).is_some() {
                        args.push(command_line.next().unwrap().clone());
                    }
                }
            }

            _ => {
                let mut ended: bool = false;
                while !ended {
                    if let Some(value) = command_line.peek() {
                        if parent.is_option(&value).is_some() {
                            ended = true;
                        } else {
                            args.push(command_line.next().unwrap().clone());
                        }
                    } else {
                        ended = true;
                    }
                }
            }
        }

        debug!("Option {:?} with arguments {:#?}", self.names, args);

        args
    }
}

#[derive(Default, Debug)]
struct PreviousCommandArgs<'a> {
    options: HashMap<&'a Option_, Vec<String>>,
    positionals: Vec<String>,
}

impl Command {
    pub fn is_option(&self, token: &str) -> Option<&Option_> {
        for option in self.options.iter() {
            if option.names.iter().find(|x| x.as_str() == token).is_some() {
                debug!("{} is an option of {}", token, self.name);
                return Some(option);
            }
        }

        debug!("{} is not an option of {}", token, self.name);
        None
    }

    pub fn is_subcommand(&self, token: &str) -> Option<&Command> {
        self.subcommands.iter().find(|c| c.name.as_str() == token)
    }

    fn positional_count(&self) -> usize {
        self.positionals
            .iter()
            .map(|p| match p.arguments {
                ArgumentCount::Fixed(value) => value,
                ArgumentCount::AtMostOne() => 1,
                _ => 10,
            })
            .reduce(|lhs, rhs| lhs + rhs)
            .unwrap_or(0)
            .try_into()
            .unwrap()
    }

    pub fn candidates(&self, arguments: &[String], profiles: &Vec<Profile>) -> Vec<String> {
        debug!("Completing '{}' with arguments {:#?}", self.name, arguments);

        let mut iter = arguments.iter().peekable();
        let mut final_object: Option<&Option_> = None;
        let mut used = PreviousCommandArgs::default();

        // First item is the command name - we skip that
        iter.next();

        while let Some(token) = iter.next() {
            if let Some(option) = self.is_option(token) {
                // Record the last used option
                final_object = Some(option);
                // Consume the command line
                let option_args = option.consume_args(self, &mut iter);

                // If we have not reached the end of the command line, there are other
                // options/positionals
                if iter.peek().is_some() {
                    // Remove the above from the final_object pointer
                    final_object = None;

                    // Record the names of the used option
                    used.options.insert(option, option_args);
                }
            } else {
                // If we find a token that is not the end and also not
                // recognized as an option, it has to be a positional
                if iter.peek().is_some() {
                    used.positionals.push((*token).clone());
                }
            }
        }

        debug!("Used for {}: {:#?}", self.name, used);

        if let Some(option) = final_object {
            option.available(profiles)
        } else {
            let mut available: Vec<String>;

            available = self
                .options
                .iter()
                .filter(|option| !used.options.contains_key(option))
                .flat_map(|x| x.names.iter().cloned())
                .collect();

            available.extend(self.subcommands.iter().map(|x| x.name.clone()));

            debug!(
                "Used positionals: {} - Needed: {}",
                used.positionals.len(),
                self.positionals.len()
            );
            if used.positionals.len() < self.positional_count() {
                let current_idx = used.positionals.len().min(self.positionals.len() - 1);
                let current = &self.positionals[current_idx];
                debug!("Current positional: {:#?}", current);
                available.extend(current.available(profiles));
            }

            available
        }
    }
}
