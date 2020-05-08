from e4s_cl import EXIT_SUCCESS
from e4s_cl.cli import arguments
from e4s_cl.cli.cli_view import CopyCommand
from e4s_cl.error import UniqueAttributeError, InternalError
from e4s_cl.model.profile import Profile

class ProfileCopyCommand(CopyCommand):
    """``profile copy`` subcommand."""

    def _copy_record(self, updates, key):
        ctrl = self.model.controller()
        key_attr = self.model.key_attribute
        matching = ctrl.search({key_attr: key})
        if not matching:
            self.parser.error("No %s-level %s with %s='%s'." % (ctrl.storage.name, self.model_name, key_attr, key))
        elif len(matching) > 1:
            raise InternalError("More than one %s-level %s with %s='%s' exists!" %
                                (ctrl.storage.name, self.model_name, key_attr, key))
        else:
            found = matching[0]
        data = dict(found)
        data.update(updates)
        key_attr = self.model.key_attribute
        key = data[key_attr]
        try:
            ctrl.create(data)
        except UniqueAttributeError:
            self.parser.error("A %s with %s='%s' already exists" % (self.model_name, key_attr, key))
        self.logger.info("Created a new %s-level %s: '%s'.", ctrl.storage.name, self.model_name, key)
        return EXIT_SUCCESS

    def main(self, argv):
        args = self._parse_args(argv)

        data = {attr: getattr(args, attr) for attr in self.model.attributes if hasattr(args, attr)}

        key_attr = self.model.key_attribute
        try:
            data[key_attr] = getattr(args, 'copy_%s' % key_attr)
        except AttributeError:
            pass
        key = getattr(args, key_attr)

        return self._copy_record(data, key)


COMMAND = ProfileCopyCommand(Profile, __name__)
