"""
Controller definition of the MVC architecture
"""

from e4s_cl import logger
from e4s_cl.error import InternalError, UniqueAttributeError, ModelError

LOGGER = logger.get_logger(__name__)

# Suppress debugging messages in optimized code
if __debug__:
    _heavy_debug = LOGGER.debug  # pylint: disable=invalid-name
else:

    def _heavy_debug(*args, **kwargs):
        # pylint: disable=unused-argument
        pass


class Controller():
    """The "C" in `MVC`_.

    Attributes:
        model (AbstractModel): Data model.
        storage (AbstractDatabase): Record storage. 
    
    .. _MVC: https://en.wikipedia.org/wiki/Model-view-controller
    """

    messages = {}

    def __init__(self, model_cls, storage):
        self.model = model_cls
        self.storage = storage

    @classmethod
    def push_to_topic(cls, topic, message):
        cls.messages.setdefault(topic, []).append(message)

    @classmethod
    def pop_topic(cls, topic):
        return cls.messages.pop(topic, [])

    def one(self, key):
        """Get a record.
        
        Args:
            key: See :any:`AbstractStorage.get`.
            
        Returns:
            Model: The model for the matching record or None if no such record exists.
        """
        record = self.storage.get(key, table_name=self.model.name)
        return self.model(record) if record else None

    def all(self):
        """Get all records.
        
        Returns:
            list: Models for all records or an empty lists if no records exist.
        """
        return [
            self.model(record)
            for record in self.storage.search(table_name=self.model.name)
        ]

    def count(self):
        """Return the number of records.
        
        Returns:
            int: Effectively ``len(self.all())``
        """
        return self.storage.count(table_name=self.model.name)

    def search(self, keys=None):
        """Return records that have all given keys.
        
        Args:
            keys: See :any:`AbstractStorage.search`.
            
        Returns:
            list: Models for records with the given keys or an empty lists if no records have all keys.
        """
        return [
            self.model(record)
            for record in self.storage.search(keys=keys,
                                              table_name=self.model.name)
        ]

    def match(self, field, regex=None, test=None):
        """Return records that have a field matching a regular expression or test function.
        
        Args:
            field: See :any:`AbstractStorage.match`.
            regex: See :any:`AbstractStorage.match`.
            test: See :any:`AbstractStorage.match`.
            
        Returns:
            list: Models for records that have a matching field.
        """
        return [
            self.model(record) for record in self.storage.match(
                field, table_name=self.model.name, regex=regex, test=test)
        ]

    def exists(self, keys):
        """Check if a record exists.
        
        Args:
            keys: See :any:`AbstractStorage.exists`.
            
        Returns:
            bool: True if a record matching `keys` exists, False otherwise.
        """
        return self.storage.contains(keys, table_name=self.model.name)

    def _check_unique(self, data, match_any=True):
        unique = {
            attr: data[attr]
            for attr, props in self.model.attributes.items()
            if 'unique' in props
        }
        if unique and self.storage.contains(
                unique, match_any=match_any, table_name=self.model.name):
            raise UniqueAttributeError(self.model, unique)

    def create(self, data):
        """Atomically store a new record
        
        Invokes the `on_create` callback **after** the data is recorded.  If this callback raises
        an exception then the operation is reverted.
        
        Args:
            data (dict): Data to record.
            
        Returns:
            Model: The newly created data. 
        """
        data = self.model.validate(data)
        self._check_unique(data)
        with self.storage as database:
            record = database.insert(data, table_name=self.model.name)
            model = self.model(record)
            model.check_compatibility(model)
            model.on_create()
            return model

    def update(self, data, keys):
        """Change recorded data
        
        The behavior depends on the type of `keys`:
            * Record.ElementIdentifier: update the record with that element identifier.
            * dict: update all records with attributes matching `keys`.
            * list or tuple: apply update to all records matching the elements of `keys`.
            * ``bool(keys) == False``: raise ValueError.
            
        Invokes the `on_update` callback **after** the data is modified.  If this callback raises
        an exception then the operation is reverted.

        Args:
            data (dict): New data for existing records.
            keys: Fields or element identifiers to match.
        """
        old_records = self.search(keys)

        if not old_records:
            raise ModelError(self.model,
                             f"No matching models for query {keys}")

        for attr, value in data.items():
            if attr not in self.model.attributes:
                raise ModelError(self.model, f"no attribute named '{attr}'")

            if attr == self.model.key_attribute:
                if len(old_records) > 1:
                    raise ModelError(
                        self.model,
                        f"Updating {len(old_records)} {self.model.name.lower()}s"
                        f" with {attr}={value} would break unicity rules")

                existing_record = self.one({attr: value})
                if existing_record and existing_record not in old_records:
                    raise UniqueAttributeError(self.model, {attr: value})

        with self.storage as database:
            # Get the list of affected records **before** updating the data so foreign keys are correct
            database.update(data, keys, table_name=self.model.name)
            changes = {}
            for model in old_records:
                changes[model.eid] = {
                    attr: (model.get(attr), new_value)
                    for attr, new_value in data.items()
                    if not (attr in model and model.get(attr) == new_value)
                }
            updated_records = self.search(keys)
            for model in updated_records:
                model.check_compatibility(model)
                model.on_update(changes[model.eid])

    def unset(self, fields, keys):
        """Unset recorded data fields
        
        The behavior depends on the type of `keys`:
            * Record.ElementIdentifier: update the record with that element identifier.
            * dict: update all records with attributes matching `keys`.
            * list or tuple: apply update to all records matching the elements of `keys`.
            * ``bool(keys) == False``: raise ValueError.

        Invokes the `on_update` callback **after** the data is modified.  If this callback raises
        an exception then the operation is reverted.

        Args:
            fields (list): Names of fields to unset.
            keys: Fields or element identifiers to match.
        """
        for attr in fields:
            if attr not in self.model.attributes:
                raise ModelError(self.model, f"no attribute named '{attr}'")
        with self.storage as database:
            # Get the list of affected records **before** updating the data so foreign keys are correct
            old_records = self.search(keys)
            database.unset(fields, keys, table_name=self.model.name)
            changes = {}
            for model in old_records:
                changes[model.eid] = {
                    attr: (model.get(attr), None)
                    for attr in fields if attr in model
                }
            updated_records = self.search(keys)
            for model in updated_records:
                model.check_compatibility(model)
                model.on_update(changes[model.eid])

    def delete(self, keys):
        """Delete recorded data
        
        The behavior depends on the type of `keys`:
            * Record.ElementIdentifier: delete the record with that element identifier.
            * dict: delete all records with attributes matching `keys`.
            * list or tuple: delete all records matching the elements of `keys`.
            * ``bool(keys) == False``: raise ValueError.

        Invokes the `on_delete` callback **after** the data is deleted.  If this callback raises
        an exception then the operation is reverted.

        Args:
            keys (dict): Attributes to match.
            keys: Fields or element identifiers to match.
        """
        with self.storage as database:
            removed_data = []
            changing = self.search(keys)
            for model in changing:
                removed_data.append(dict(model))
            database.remove(keys, table_name=self.model.name)
            for model in changing:
                model.on_delete()

    @staticmethod
    def import_records(data):
        """Import data records.
        
        TODO: Docs
        """

    @classmethod
    def export_records(cls, keys=None, eids=None):
        """Export data records.
        
        Constructs a dictionary containing records matching `keys` or `eids`

        Args:
            keys (dict): Attributes to match.
            eids (list): Record identifiers to match.

        Returns:
            dict: Dictionary of tables containing records.
            
        Example:
        ::
            
            {
             'Brewery': {100: {'address': '4615 Hollins Ferry Rd, Halethorpe, MD 21227',
                               'brews': [10, 12, 14]}},
             'Beer': {10: {'origin': 100, 'color': 'gold', 'ibu': 45},
                      12: {'origin': 100, 'color': 'dark', 'ibu': 15},
                      14: {'origin': 100, 'color': 'pale', 'ibu': 30}}
            }
        
            Beer.export_records(eids=[10])
            
            {
             'Brewery': {100: {'address': '4615 Hollins Ferry Rd, Halethorpe, MD 21227',
                               'brews': [10, 12, 14]}},
             'Beer': {10: {'origin': 100, 'color': 'gold', 'ibu': 45}}
            }

        """

        def export_record(record, root):
            if isinstance(record, cls) and record is not root:
                return
            data = all_data.setdefault(record.model_name, {})
            if record.eid not in data:
                data[record.eid] = record.data

        all_data = {}
        for record in cls.search(keys, eids):
            export_record(record, record)
        return all_data
