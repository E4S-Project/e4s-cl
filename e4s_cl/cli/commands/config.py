import sys
import yaml
from pathlib import Path
from e4s_cl import EXIT_SUCCESS, EXIT_FAILURE, logger
from e4s_cl.cli import arguments
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.config import ALLOWED_CONFIG, USER_CONFIG_PATH, ConfigurationError, Configuration
from e4s_cl.util import mkdirp

LOGGER = logger.get_logger(__name__)


def _update_config(config_file, key, value):
    config = {}
    if config_file and Path(config_file).exists():
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f) or {}

    # Navigate to the correct position
    parts = key.split('.')
    current = config
    
    # Check if the split by dot was correct by validating against allowed keys
    # This is a heuristic: we reconstruct the flattened key and check if it exists
    flattened_key = "_".join(parts)
    allowed_keys = {f.key: f for f in ALLOWED_CONFIG.flatten()}
    
    if flattened_key not in allowed_keys:
        LOGGER.error(f"Invalid configuration key '{key}'. Available keys: {', '.join(allowed_keys.keys())}")
        return False
    
    field_info = allowed_keys[flattened_key]
    
    # Cast value
    try:
        if field_info.expected_type is bool:
             if value.lower() in ['true', 'yes', '1']:
                 cast_value = True
             elif value.lower() in ['false', 'no', '0']:
                 cast_value = False
             else:
                 raise ValueError("Not a boolean")
        else:
            cast_value = field_info.expected_type(value)
    except ValueError:
        LOGGER.error(f"Invalid value '{value}' for key '{key}'. Expected type: {field_info.expected_type.__name__}")
        return False

    # Set value
    # We need to preserve the structure derived from the allowed config group structure, 
    # but ALLOWED_CONFIG is flattened with underscores, while YAML is nested.
    # The config.py flatten() uses underscores.
    # We need to map flattened key to nested dict structure for YAML.
    # However, since attributes can contain underscores, splitting by underscore is ambiguous.
    # E.g. 'disable_ranked_log' is a top level key with underscores.
    # 'wi4mpi_install_directory' is 'wi4mpi' -> 'install_directory'.
    
    # We can try to match prefixes with the groups in ALLOWED_CONFIG.
    
    def set_recursive(current_dict, key_parts, value):
        if not key_parts:
            return
            
        head = key_parts[0]
        if len(key_parts) == 1:
            current_dict[head] = value
        else:
            if head not in current_dict:
                current_dict[head] = {}
            if not isinstance(current_dict[head], dict):
                 # This should not happen if the schema matches, but safety first
                 current_dict[head] = {}
            set_recursive(current_dict[head], key_parts[1:], value)

    # We need to decompose the flattened key back into the nested structure.
    # We can walk the ALLOWED_CONFIG groups.
    
    parts_path = []
    
    def find_path(group, target_key):
        for field in group.fields:
            if hasattr(field, 'fields'): # Group
                 path = find_path(field, target_key)
                 if path is not None:
                     return [group.key] + path
            else: # Field
                 # Construct full key to check match
                 namespaced = "_".join(filter(None, [group.key, field.key])) # This is relative to the group passed
                 # But ALLOWED_CONFIG is root.
                 pass

    # Easier approach: Iterate over allowed keys, and since we found the matching field,
    # we just need to know its path. config.py doesn't expose the path easily.
    # But we can reconstruct it.
    
    # Re-implement simple path finder
    def get_path_segments(group, flat_key):
        for field in group.fields:
            if hasattr(field, 'fields'): # It's a group
                 # Check if flat_key starts with the child group's key
                 prefix = field.key + "_" if field.key else ""
                 
                 if flat_key.startswith(prefix):
                      suffix = flat_key[len(prefix):]
                      res = get_path_segments(field, suffix)
                      if res is not None:
                           return [field.key] + res if field.key else res
            else:
                 if field.key == flat_key:
                      return [field.key]
        return None

    segments = get_path_segments(ALLOWED_CONFIG, flattened_key)
    
    if not segments:
         LOGGER.error(f"Could not resolve key '{key}' to configuration structure.")
         return False

    set_recursive(config, segments, cast_value)

    if not mkdirp(Path(config_file).parent):
        LOGGER.error(f"Could not create directory for {config_file}")
        return False
        
    with open(config_file, 'w') as f:
        yaml.safe_dump(config, f, default_flow_style=False)
        
    return True

def unflatten(flat_dict):
    """
    Reverse the flattening process: 'wi4mpi_install_directory' -> {'wi4mpi': {'install_directory': ...}}
    We need to know the schema to do this correctly to handle nested keys vs keys with underscores.
    Using ALLOWED_CONFIG to guide unflattening.
    """
    nested = {}
    
    # We reuse the set_recursive logic but applied to the whole dict
    def set_recursive(current_dict, key_parts, value):
        if not key_parts:
            return
            
        head = key_parts[0]
        if len(key_parts) == 1:
            current_dict[head] = value
        else:
            if head not in current_dict:
                current_dict[head] = {}
            if not isinstance(current_dict[head], dict): # pragma: no cover
                 current_dict[head] = {}
            set_recursive(current_dict[head], key_parts[1:], value)
            
    def get_path_segments(group, flat_key):
        for field in group.fields:
            if hasattr(field, 'fields'): # It's a group
                 if not group.key or flat_key.startswith(group.key + "_"):
                      if group.key:
                           suffix = flat_key[len(group.key)+1:]
                      else:
                           suffix = flat_key
                      res = get_path_segments(field, suffix)
                      if res is not None:
                           return [group.key] + res if group.key else res
            else:
                 if field.key == flat_key: # Relative key check?
                     # No, flat_key is passed as suffix.
                     # If we are at root, flat_key is full key.
                     # If field.key matches flat_key, we found it?
                     pass
                 
                 # Reconstruct namespaced key to check against flat_key
                 # But we don't know the exact prefix logic in the loop easily without passing it down.
                 pass

    # Simplified unflatten using ALLOWED_CONFIG structure mapping
    # We iterate over the flat_dict, and for each key, we find its path in ALLOWED_CONFIG.
    
    # Pre-compute mapping from flat key to path
    flat_key_to_path = {}
    
    def map_keys(group, prefix_path):
        for field in group.fields:
            if hasattr(field, 'fields'):
                new_path = prefix_path + [group.key] if group.key else prefix_path
                map_keys(field, new_path)
            else:
                # Leaf
                # Construct flattened key
                # Wait, config.py flatten() uses _join(filter(None, [self.key, field.key]))
                # But it only goes one level up? No, it's recursive.
                
                # Let's rely on the fact that we can call allowed_config.flatten() to get all valid keys
                pass

    # Actually, config.py's flatten yields fields with FULL keys (namespaced).
    # So we can just map those full keys back to their components.
    # But ConfigurationGroup doesn't store the path components in the flattened fields, only the joined string.
    
    # Let's build a map by traversing the tree.
    key_path_map = {}
    
    def traverse(group, current_path):
         # current_path is a list of keys
         for field in group.fields:
             if hasattr(field, 'fields'):
                 new_path = current_path + [field.key]
                 traverse(field, new_path)
             else:
                 # field is configuration field
                 # Calculate flattened key
                 # The flattening logic in config.py is:
                 # namespaced = "_".join(filter(None, [self.key, field.key]))
                 # But it happens recursively.
                 # Actually, looking at config.py flatten():
                 # It recursively calls flatten(), then prepends self.key to the result.
                 
                 # So for a deeply nested field, the key is group1_group2_field.
                 
                 full_path = current_path + [field.key]
                 flat_key = "_".join(filter(None, full_path))
                 key_path_map[flat_key] = full_path
                 
    traverse(ALLOWED_CONFIG, []) # Root group key is "" so we pass empty list.
    
    for flat_key, value in flat_dict.items():
        if flat_key in key_path_map:
            path = key_path_map[flat_key]
            set_recursive(nested, path, value)
        else:
            # Unknown key, maybe just leave it at top level?
            nested[flat_key] = value
            
    return nested

class ConfigCommand(AbstractCommand):
    """
    Manage the configuration.
    """
    def _construct_parser(self):
        parser = arguments.get_parser(prog=self.command, description=self.summary)
        subparsers = parser.add_subparsers(dest='action', help='Action to perform')
        
        # list
        list_parser = subparsers.add_parser('list', help='List configuration options')

        # set
        set_parser = subparsers.add_parser('set', help='Set a configuration option')
        set_parser.add_argument('key', help='Configuration key (can use dot notation, e.g. wi4mpi.install_directory)')
        set_parser.add_argument('value', help='Value to set')
        
        # get
        get_parser = subparsers.add_parser('get', help='Get a configuration option value')
        get_parser.add_argument('key', help='Configuration key (can use dot or underscore notation)')
        
        return parser

    def main(self, argv):
        args = self._parse_args(argv)
        if not args.action:
             print(self.parser.format_help())
             return EXIT_FAILURE
        
        if args.action == 'list':
             # pretty print the current merged configuration
             from e4s_cl.config import CONFIGURATION
             # CONFIGURATION._fields is the flat dict
             nested = unflatten(CONFIGURATION._fields)
             print(yaml.safe_dump(nested, default_flow_style=False))
             return EXIT_SUCCESS
             
        elif args.action == 'set':
             key = args.key.replace('.', '_')
             if _update_config(USER_CONFIG_PATH, key, args.value):
                 print(f"Updated {USER_CONFIG_PATH}")
                 return EXIT_SUCCESS
             else:
                 return EXIT_FAILURE
                 
        elif args.action == 'get':
             from e4s_cl.config import CONFIGURATION
             key = args.key.replace('.', '_')
             try:
                 val = getattr(CONFIGURATION, key)
                 print(val)
                 return EXIT_SUCCESS
             except AttributeError:
                 LOGGER.error(f"Key '{key}' not found in configuration.")
                 return EXIT_FAILURE
                 
        return EXIT_SUCCESS

COMMAND = ConfigCommand(__name__, summary_fmt="Configuration management")
