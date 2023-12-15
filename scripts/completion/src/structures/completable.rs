use crate::structures::{Command, ExpectedType, Option_, Positional, Profile};
use itertools::Itertools;

pub trait Completable {
    fn available(&self, profiles: &Vec<Profile>) -> Vec<String>;
}

impl Completable for Positional {
    fn available(&self, profiles: &Vec<Profile>) -> Vec<String> {
        match self.expected_type {
            ExpectedType::Profile() => profiles.iter().map(|x| x.name.clone()).collect(),
            _ => vec![],
        }
    }
}

impl Completable for Option_ {
    fn available(&self, profiles: &Vec<Profile>) -> Vec<String> {
        match self.expected_type {
            ExpectedType::Profile() => profiles.iter().map(|x| x.name.clone()).collect(),
            _ => self.values.clone(),
        }
    }
}

impl Completable for Command {
    fn available(&self, profiles: &Vec<Profile>) -> Vec<String> {
        let mut available: Vec<String>;

        available = self
            .options
            .iter()
            .flat_map(|x| x.names.iter().cloned())
            .collect();

        available.extend(self.subcommands.iter().map(|x| x.name.clone()));

        available.extend(
            self.positionals
                .iter()
                .map(|x| x.available(profiles))
                .flatten()
                .unique()
                .collect::<Vec<String>>(),
        );

        available
    }
}
