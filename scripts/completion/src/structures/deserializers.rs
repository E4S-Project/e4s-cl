use crate::structures::{ArgumentCount, ExpectedType};
use serde::de::{Deserializer, Error, Unexpected, Visitor};
struct ArgumentVisitor;

impl<'de> Visitor<'de> for ArgumentVisitor {
    type Value = ArgumentCount;

    fn expecting(&self, formatter: &mut std::fmt::Formatter) -> std::fmt::Result {
        formatter.write_str("enum ArgumentCount")
    }

    fn visit_u64<E>(self, u: u64) -> Result<Self::Value, E>
    where
        E: Error,
    {
        Ok(ArgumentCount::Fixed(u))
    }

    fn visit_str<E>(self, s: &str) -> Result<Self::Value, E>
    where
        E: Error,
    {
        match s {
            "ARGS_SOME" => Ok(ArgumentCount::Any()),
            "ARGS_ATLEASTONE" => Ok(ArgumentCount::AtLeastOne()),
            "ARGS_ATMOSTONE" => Ok(ArgumentCount::AtMostOne()),
            _ => Err(Error::invalid_value(Unexpected::Str(s), &self)),
        }
    }
}

pub fn argument_count_de<'de, D>(deserializer: D) -> Result<ArgumentCount, D::Error>
where
    D: Deserializer<'de>,
{
    deserializer.deserialize_any(ArgumentVisitor)
}

struct TypeVisitor;

impl<'de> Visitor<'de> for TypeVisitor {
    type Value = ExpectedType;

    fn expecting(&self, formatter: &mut std::fmt::Formatter) -> std::fmt::Result {
        formatter.write_str("enum ExpectedType")
    }

    fn visit_str<E>(self, s: &str) -> Result<Self::Value, E>
    where
        E: Error,
    {
        match s {
            "DEFINED_PROFILE" => Ok(ExpectedType::Profile()),
            _ => Ok(ExpectedType::Unknown()),
        }
    }
}

pub fn expected_type_de<'de, D>(deserializer: D) -> Result<ExpectedType, D::Error>
where
    D: Deserializer<'de>,
{
    deserializer.deserialize_string(TypeVisitor)
}
