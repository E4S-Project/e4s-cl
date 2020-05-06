from e4s_cl import logger
from e4s_cl.error import InternalError, UniqueAttributeError, ModelError

LOGGER = logger.get_logger(__name__)

# Suppress debugging messages in optimized code
if __debug__:
    _heavy_debug = LOGGER.debug   # pylint: disable=invalid-name
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
        return [self.model(record) for record in self.storage.search(table_name=self.model.name)]
    
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
        return [self.model(record) for record in self.storage.search(keys=keys, table_name=self.model.name)]

    def match(self, field, regex=None, test=None):
        """Return records that have a field matching a regular expression or test function.
        
        Args:
            field: See :any:`AbstractStorage.match`.
            regex: See :any:`AbstractStorage.match`.
            test: See :any:`AbstractStorage.match`.
            
        Returns:
            list: Models for records that have a matching field.
        """
        return [self.model(record) 
                for record in self.storage.match(field, table_name=self.model.name, regex=regex, test=test)]

    def exists(self, keys):
        """Check if a record exists.
        
        Args:
            keys: See :any:`AbstractStorage.exists`.
            
        Returns:
            bool: True if a record matching `keys` exists, False otherwise.
        """
        return self.storage.contains(keys, table_name=self.model.name)

    def populate(self, model, attribute=None, defaults=False):
        """Merges associated data into the model record.
        
        Example:
            Suppose we have the following Person records::
            
                1: {'name': 'Katie', 'friends': [2, 3]}
                2: {'name': 'Ryan', 'friends': [1]}
                3: {'name': 'John', 'friends': [1]}

            Populating ``Person({'name': 'Katie', 'friends': [2, 3]})`` produces this dictionary::
            
                {'name': 'Katie',
                 'friends': [Person({'name': 'Ryan', 'friends': [1]}),
                             Person({'name': 'John', 'friends': [1]}]})
                             
        Args:
            attribute (Optional[str]): If given, return only the populated attribute.
            defaults (Optional[bool]): If given, set undefined attributes to their default values.
        
        Returns:
            If attribute is None, a dictionary of controlled data merged with associated records.
            If attribute is not None, the value of the populated attribute. 
            
        Raises:
            KeyError: `attribute` is undefined in the record. 
        """
        if attribute:
            _heavy_debug("Populating %s(%s)[%s]", model.name, model.eid, attribute)
            return self._populate_attribute(model, attribute, defaults)

        _heavy_debug("Populating %s(%s)", model.name, model.eid)
        return {attr: self._populate_attribute(model, attr, defaults) for attr in model}

    def _populate_attribute(self, model, attr, defaults):
        try:
            props = model.attributes[attr]
        except KeyError:
            raise ModelError(model, "no attribute '%s'" % attr)
        if not defaults or 'default' not in props:
            value = model[attr]
        else:
            value = model.get(attr, props['default'])
        try:
            foreign = props['model']
        except KeyError:
            try:
                foreign = props['collection']
            except KeyError:
                return value
            else:
                return foreign.controller(self.storage).search(value)
        else:
            return foreign.controller(self.storage).one(value)

    def _check_unique(self, data, match_any=True):
        unique = {attr: data[attr] for attr, props in self.model.attributes.items() if 'unique' in props}
        if unique and self.storage.contains(unique, match_any=match_any, table_name=self.model.name):
            raise UniqueAttributeError(self.model, unique)
    
    def create(self, data):
        """Atomically store a new record and update associations.
        
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
            for attr, foreign in self.model.associations.items():
                if 'model' or 'collection' in self.model.attributes[attr]:
                    affected = record.get(attr, None)
                    if affected:
                        foreign_cls, via = foreign
                        self._associate(record, foreign_cls, affected, via)
            model = self.model(record)
            model.check_compatibility(model)
            model.on_create()
            return model
    
    def update(self, data, keys):
        """Change recorded data and update associations.
        
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
        for attr in data:
            if attr not in self.model.attributes:
                raise ModelError(self.model, "no attribute named '%s'" % attr)
        with self.storage as database:
            # Get the list of affected records **before** updating the data so foreign keys are correct
            old_records = self.search(keys)
            database.update(data, keys, table_name=self.model.name)
            changes = {}
            for model in old_records:
                changes[model.eid] = {attr: (model.get(attr), new_value) for attr, new_value in data.items()
                                      if not (attr in model and model.get(attr) == new_value)}
                for attr, foreign in self.model.associations.items():
                    try:
                        # 'collection' attribute is iterable
                        new_foreign_keys = set(data[attr])
                    except TypeError:
                        # 'model' attribute is not iterable, so make a tuple
                        new_foreign_keys = set((data[attr],))
                    except KeyError:
                        continue
                    try:
                        # 'collection' attribute is iterable
                        old_foreign_keys = set(model[attr])
                    except TypeError:
                        # 'model' attribute is not iterable, so make a tuple
                        old_foreign_keys = set((model[attr],))
                    except KeyError:
                        old_foreign_keys = set()
                    foreign_cls, via = foreign
                    added = list(new_foreign_keys - old_foreign_keys)
                    deled = list(old_foreign_keys - new_foreign_keys)
                    if added:
                        self._associate(model, foreign_cls, added, via)
                    if deled:
                        self._disassociate(model, foreign_cls, deled, via)
            updated_records = self.search(keys)
            for model in updated_records:
                model.check_compatibility(model)
                model.on_update(changes[model.eid])

    def unset(self, fields, keys):
        """Unset recorded data fields and update associations.
        
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
                raise ModelError(self.model, "no attribute named '%s'" % attr)
        with self.storage as database:
            # Get the list of affected records **before** updating the data so foreign keys are correct
            old_records = self.search(keys)
            database.unset(fields, keys, table_name=self.model.name)
            changes = {}
            for model in old_records:
                changes[model.eid] = {attr: (model.get(attr), None) for attr in fields if attr in model}
                for attr, foreign in self.model.associations.items():
                    if attr in fields:
                        foreign_cls, via = foreign
                        old_foreign_keys = model.get(attr, None)
                        if old_foreign_keys:
                            self._disassociate(model, foreign_cls, old_foreign_keys, via)
            updated_records = self.search(keys)
            for model in updated_records:
                model.check_compatibility(model)
                model.on_update(changes[model.eid])

    def delete(self, keys):
        """Delete recorded data and update associations.
        
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
                for attr, foreign in model.associations.items():
                    foreign_model, via = foreign
                    affected_keys = model.get(attr, None)
                    if affected_keys:
                        _heavy_debug("Deleting %s(%s) affects '%s' in %s(%s)", 
                                     self.model.name, model.eid, via, foreign_model.name, affected_keys)
                        self._disassociate(model, foreign_model, affected_keys, via)
                for foreign_model, via in model.references:
                    # pylint complains because `model` is changing on every iteration so we'll have
                    # a different lambda function `test` on each iteration.  This is exactly what
                    # we want so we disble the warning. 
                    # pylint: disable=cell-var-from-loop, undefined-loop-variable
                    test = lambda x: model.eid in x if isinstance(x, list) else model.eid == x
                    affected = database.match(via, test=test, table_name=foreign_model.name)
                    affected_keys = [record.eid for record in affected]
                    if affected_keys:
                        _heavy_debug("Deleting %s(%s) affects '%s' in %s(%s)", 
                                     self.model.name, model.eid, via, foreign_model.name, affected_keys)
                        self._disassociate(model, foreign_model, affected_keys, via)
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
        
        Constructs a dictionary containing records matching `keys` or `eids` and all their
        associated records.  Association fields (`model` and `collection`) are **not** updated
        and may contain eids of undefined records. 

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
                for attr, foreign in record.associations.items():
                    for foreign_record in foreign[0].search(eids=record[attr]):
                        export_record(foreign_record, root)
        all_data = {}
        for record in cls.search(keys, eids):
            export_record(record, record)
        return all_data
          
    def _associate(self, record, foreign_model, affected, via):
        """Associates a record with another record.
        
        Args:
            record (Record): Record to associate.
            foreign_model (Model): Foreign record's data model.
            affected (list): Identifiers for the records that will be updated to associate with `record`.
            via (str): The name of the associated foreign attribute.
        """ 
        _heavy_debug("Adding %s to '%s' in %s(eids=%s)", record.eid, via, foreign_model.name, affected)
        if not isinstance(affected, list):
            affected = [affected]
        with self.storage as database:
            for key in affected:
                foreign_record = database.get(key, table_name=foreign_model.name)
                if not foreign_record:
                    raise ModelError(foreign_model, "No record with ID '%s'" % key)
                if 'model' in foreign_model.attributes[via]:
                    updated = record.eid
                elif 'collection' in foreign_model.attributes[via]:
                    updated = list(set(foreign_record[via] + [record.eid]))
                else:
                    raise InternalError("%s.%s has neither 'model' nor 'collection'" % (foreign_model.name, via))
                foreign_model.controller(database).update({via: updated}, key)

    def _disassociate(self, record, foreign_model, affected, via):
        """Disassociates a record from another record.
        
        Args:
            record (Record): Record to disassociate.
            foreign_model (Model): Foreign record's data model.
            affected (list): Identifiers for the records that will be updated to disassociate from `record`.
            via (str): The name of the associated foreign attribute.
        """ 
        _heavy_debug("Removing %s from '%s' in %s(eids=%s)", record.eid, via, foreign_model.name, affected)
        if not isinstance(affected, list):
            affected = [affected]
        foreign_props = foreign_model.attributes[via]
        if 'model' in foreign_props:
            if 'required' in foreign_props:
                _heavy_debug("Empty required attr '%s': deleting %s(keys=%s)", via, foreign_model.name, affected)
                foreign_model.controller(self.storage).delete(affected)
            else:
                with self.storage as database:
                    database.unset([via], affected, table_name=foreign_model.name)
        elif 'collection' in foreign_props:
            with self.storage as database:
                for key in affected:
                    foreign_record = database.get(key, table_name=foreign_model.name)
                    updated = list(set(foreign_record[via]) - set([record.eid]))
                    if 'required' in foreign_props and len(updated) == 0:
                        _heavy_debug("Empty required attr '%s': deleting %s(key=%s)", via, foreign_model.name, key)
                        foreign_model.controller(database).delete(key)
                    else:
                        database.update({via: updated}, key, table_name=foreign_model.name)
