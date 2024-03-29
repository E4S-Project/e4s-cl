"""
Model definition of the MVC architecture
"""

from e4s_cl import logger
from e4s_cl.error import IncompatibleRecordError, ModelError, InternalError
from e4s_cl.cf.storage import StorageRecord
from e4s_cl.mvc.controller import Controller

LOGGER = logger.get_logger(__name__)


class ModelMeta(type):
    """Constructs model attributes, configures defaults, and establishes relationships."""

    def __new__(mcs, name, bases, dct):
        if dct['__module__'] != __name__:
            # Each Model subclass has its own relationships
            dct.update({'associations': {}, 'references': set()})
            # The default model name is the class name
            if dct.get('name', None) is None:
                dct['name'] = name
            # Model subclasses must define __attributes__ as a callable.
            # We make the callable a staticmethod to prevent method binding.
            try:
                dct['__attributes__'] = staticmethod(dct['__attributes__'])
            except KeyError as err:
                raise InternalError(
                    f"Model class {name} does not define '__attributes__'"
                ) from err
            # Replace attributes with a callable property (defined below).  This is to guarantee
            # that model attributes won't be constructed until all Model subclasses have been constructed.
            dct['attributes'] = ModelMeta.attributes
            # Replace key_attribute with a callable property (defined below). This is to set
            # the key_attribute member after the model attributes have been constructed.
            dct['key_attribute'] = ModelMeta.key_attribute
        return type.__new__(mcs, name, bases, dct)

    @property
    def attributes(cls):
        # pylint: disable=attribute-defined-outside-init
        try:
            return cls._attributes
        except AttributeError:
            cls._attributes = cls.__attributes__()
            cls._construct_relationships()
            return cls._attributes

    @property
    def key_attribute(cls):
        """
        Get the key attribute of a class
        """
        # pylint: disable=no-value-for-parameter
        try:
            return cls._key_attribute
        except AttributeError as err:
            for attr, props in cls.attributes.items():
                if 'primary_key' in props:
                    cls._key_attribute = attr
                    break
            else:
                raise ModelError(
                    cls,
                    "No attribute has the 'primary_key' property set to 'True'"
                ) from err
            return cls._key_attribute


class Model(StorageRecord, metaclass=ModelMeta):
    """The "M" in `MVC`_.

    Attributes:
        name (str): Name of the model.
        associations (dict): (Controller, str) tuples keyed by attribute name defining attribute associations.
        references (set): (Controller, str) tuples listing foreign models referencing this model.  
        attributes (dict): Model attributes.
        key_attribute (str): Name of an attribute that serves as a unique identifier. 
        
    .. _MVC: https://en.wikipedia.org/wiki/Model-view-controller
    """

    __controller__ = Controller
    __attributes__ = NotImplemented

    name = None
    associations = {}
    references = set()
    attributes = {}
    key_attribute = None

    def __init__(self, record):
        deprecated = [attr for attr in record if attr not in self.attributes]
        if deprecated:
            try:
                title = f"{self.name} '{record[self.key_attribute]}'"
            except (KeyError, ModelError):
                title = f"{self.name}"
            LOGGER.debug("Ignorning deprecated attributes %s in %s",
                         deprecated, title)
        super().__init__(
            record.storage, record.eid,
            (item for item in record.items() if item[0] not in deprecated))

    def __setitem__(self, key, value):
        raise InternalError(
            "Use controller(storage).update() to alter records")

    def __delitem__(self, key):
        raise InternalError(
            "Use controller(storage).update() to alter records")

    def get_or_default(self, key):
        """Returns the attribute's value or default value.
        
        Args:
            key (str): Attribute name.
        
        Returns:
            If the attribute is set then the attribute's value is returned.
            If the attribute is not set then the attribute's default value is returned.

        Raises:
            If the attribute is not set and has no default value then a KeyError is raised.
        """
        try:
            return self[key]
        except KeyError:
            return self.attributes[key]['default']

    def on_create(self):
        """Callback to be invoked after a new data record is created."""

    def on_update(self, changes):
        """Callback to be invoked after a data record is updated."""

    def on_delete(self):
        """Callback to be invoked before a data record is deleted."""

    @classmethod
    def controller(cls, storage):
        return cls.__controller__(cls, storage)

    @classmethod
    def _construct_relationships(cls):
        primary_key = None
        for attr, props in cls.attributes.items():
            model_attr_name = cls.name + "." + attr
            if 'collection' in props and 'via' not in props:
                raise ModelError(
                    cls,
                    f"{model_attr_name}: collection does not define 'via'")
            if 'via' in props and not ('collection' in props
                                       or 'model' in props):
                raise ModelError(
                    cls,
                    f"{model_attr_name}: defines 'via' property but not 'model'"
                    "or 'collection'")
            if not isinstance(props.get('unique', False), bool):
                raise ModelError(
                    cls, f"{model_attr_name}: invalid value for 'unique'")
            if not isinstance(props.get('description', ''), str):
                raise ModelError(
                    cls, f"{model_attr_name}: invalid value for 'description'")
            if props.get('primary_key', False):
                if primary_key is not None:
                    raise ModelError(
                        cls,
                        f"{model_attr_name}: primary key previously specified "
                        f"as {primary_key}")
                primary_key = attr

            via = props.get('via', None)
            foreign_cls = props.get('model', props.get('collection', None))
            if not foreign_cls:
                continue
            try:
                if not issubclass(foreign_cls, Model):
                    raise TypeError
            except TypeError as err:
                raise ModelError(
                    cls,
                    f"{model_attr_name}: Invalid foreign model controller: "
                    f"{foreign_cls}") from err

            forward = (foreign_cls, via)
            reverse = (cls, attr)
            if not via:
                foreign_cls.references.add(reverse)
            else:
                foreign_cls.associations[via] = reverse
                foreign_model_attr_name = foreign_cls.name + "." + via
                try:
                    via_props = foreign_cls.attributes[via]
                except KeyError as err:
                    raise ModelError(
                        cls, f"{model_attr_name}: 'via' references undefined "
                        f"attribute '{foreign_model_attr_name}'") from err
                via_attr_model = via_props.get(
                    'model', via_props.get('collection', None))
                if not via_attr_model:
                    raise ModelError(
                        cls,
                        f"{model_attr_name}: 'via' on non-model attribute "
                        f"'{foreign_model_attr_name}'")
                if via_attr_model is not cls:
                    raise ModelError(
                        cls,
                        f"Attribute '{foreign_model_attr_name}' referenced by "
                        f"'via' in '{attr}' does not define 'collection' or "
                        f"'model' of type '{cls.name}'")
                try:
                    existing = cls.associations[attr]
                except KeyError:
                    cls.associations[attr] = forward
                else:
                    if existing != forward:
                        raise ModelError(
                            cls,
                            f"{model_attr_name}: conflicting associations: "
                            f"'{existing}' vs. '{forward}'")

    @classmethod
    def validate(cls, data):
        """Validates data against the model.
        
        Args:
            data (dict): Data to validate, may be None.

        Returns:
            dict: Validated data or None if `data` is None.
            
        Raises:
            ModelError: The given data doesn't fit the model.
        """
        if data is None:
            return None
        for key in data:
            if key not in cls.attributes:
                raise ModelError(cls, f"no attribute named '{key}'")
        validated = {}
        for attr, props in cls.attributes.items():
            # Check required fields and defaults
            try:
                validated[attr] = data[attr]
            except KeyError as err:
                if 'required' in props:
                    if props['required']:
                        raise ModelError(
                            cls, f"'{attr}' is required but was not defined"
                        ) from err
                elif 'default' in props:
                    validated[attr] = props['default']
            # Check collections
            if 'collection' in props:
                value = data.get(attr, [])
                if not value:
                    value = []
                elif not isinstance(value, list):
                    raise ModelError(
                        cls,
                        f"Value supplied for '{attr}' is not a list: {value}")
                else:
                    for eid in value:
                        try:
                            int(eid)
                        except ValueError as err:
                            raise ModelError(
                                cls,
                                f"Invalid non-integer ID '{eid}' in '{attr}'"
                            ) from err
                validated[attr] = value
            # Check model associations
            elif 'model' in props:
                value = data.get(attr, None)
                if value is not None:
                    try:
                        if int(value) != value:
                            raise ValueError
                    except ValueError as err:
                        raise ModelError(
                            cls,
                            f"Invalid non-integer ID '{value}' in '{attr}'"
                        ) from err
                    validated[attr] = value
        return validated

    @classmethod
    def construct_condition(cls,
                            args,
                            attr_defined=None,
                            attr_undefined=None,
                            attr_eq=None,
                            attr_ne=None):
        """Constructs a compatibility condition, see :any:`check_compatibility`.
        
        The returned condition is a callable that accepts four arguments:
            * lhs (Model): The left-hand side of the `check_compatibility` operation.
            * lhs_attr (str): Name of the attribute that defines the 'compat' property.
            * lhs_value: The value of the attribute that defines the 'compat' property.
            * rhs (Model): Controller of the data record we are checking against.
        
        The `condition` callable raises a :any:`IncompatibleRecordError` if the compared attributes 
        are fatally incompatibile, i.e. the user's operation is guaranteed to fail with the chosen 
        records. It may emit log messages to indicate that the records are not perfectly compatible 
        but that the user's operation is still likely to succeed with the chosen records.
        
        See :any:`require`, :any:`encourage`, :any:`discourage`, :any:`exclude` for common conditions.
        
        args[0] specifies a model attribute to check.  If args[1] is given, it is a value to compare 
        the specified attribute against or a callback function.  If args[1] is callable, it must check attribute 
        existance and value correctness and throw the appropriate exception and/or emit log messages.
        
        Args:
            args (tuple): Attribute name in args[0] and, optionally, attribute value in args[1].
            attr_defined: Callback function to be invoked when the attribute is defined.
            attr_undefined: Callback function to be invoked when the attribute is undefined.
            attr_eq: Callback function to be invoked when the attribute is equal to args[1].
            attr_ne: Callback function to be invoked when the attribute is not equal to args[1].

        Returns:
            Callable condition object for use with :any:`check_compatibility`.
        """
        rhs_attr = args[0]
        try:
            checked_value = args[1]
        except IndexError:

            def condition(lhs, lhs_attr, lhs_value, rhs):
                if isinstance(rhs, cls):
                    if rhs_attr in rhs:
                        if attr_defined:
                            attr_defined(lhs, lhs_attr, lhs_value, rhs,
                                         rhs_attr)
                    else:
                        if attr_undefined:
                            attr_undefined(lhs, lhs_attr, lhs_value, rhs,
                                           rhs_attr)
        else:
            if callable(checked_value):

                def condition(lhs, lhs_attr, lhs_value, rhs):
                    if isinstance(rhs, cls):
                        checked_value(lhs, lhs_attr, lhs_value, rhs, rhs_attr)
            else:

                def condition(lhs, lhs_attr, lhs_value, rhs):
                    if isinstance(rhs, cls):
                        try:
                            rhs_value = rhs[rhs_attr]
                        except KeyError:
                            if attr_undefined:
                                attr_undefined(lhs, lhs_attr, lhs_value, rhs,
                                               rhs_attr)
                        else:
                            if attr_eq:
                                if rhs_value == checked_value:
                                    attr_eq(lhs, lhs_attr, lhs_value, rhs,
                                            rhs_attr, checked_value)
                            elif attr_ne:
                                if rhs_value != checked_value:
                                    attr_ne(lhs, lhs_attr, lhs_value, rhs,
                                            rhs_attr, checked_value)
                            elif attr_defined:
                                attr_defined(lhs, lhs_attr, lhs_value, rhs,
                                             rhs_attr)

        return condition

    @classmethod
    def require(cls, *args):
        """Constructs a compatibility condition to enforce required conditions.
        
        The condition will raise a :any:`IncompatibleRecordError` if the specified attribute is
        undefined or not equal to the specified value (if given).
        
        Args:
            *args: Corresponds to `args` in :any:`construct_condition`. 
        
        Returns:
            Callable condition object for use with :any:`check_compatibility`
            
        Examples:
            'have_cheese' must be True::
            
                CheeseShop.require('have_cheese', True)
             
            'have_cheese' must be set to any value::
                
                CheeseShop.require('have_cheese')
            
            The value of 'have_cheese' will be checked for correctness by 'cheese_callback'::
            
                CheeseShop.require('have_cheese', cheese_callback)
        """

        def attr_undefined(lhs, lhs_attr, lhs_value, rhs, rhs_attr):
            lhs_name = lhs.name.lower()
            rhs_name = rhs.name.lower()
            raise IncompatibleRecordError(
                f"{lhs_attr} = {lhs_value} in {lhs_name} requires {rhs_attr} "
                f"be defined in {rhs_name} but it is undefined")

        def attr_ne(lhs, lhs_attr, lhs_value, rhs, rhs_attr, checked_value):
            lhs_name = lhs.name.lower()
            rhs_name = rhs.name.lower()
            rhs_value = rhs[rhs_attr]
            raise IncompatibleRecordError(
                f"{lhs_attr} = {lhs_value} in {lhs_name} requires {rhs_attr} "
                f"= {checked_value} in {rhs_name} but it is {rhs_value}")

        return cls.construct_condition(args,
                                       attr_undefined=attr_undefined,
                                       attr_ne=attr_ne)

    @classmethod
    def encourage(cls, *args):
        """Constructs a compatibility condition to make recommendations.
        
        The condition will emit warnings messages if the specified attribute is
        undefined or not equal to the specified value (if given).
        
        Args:
            *args: Corresponds to `args` in :any:`construct_condition`. 
        
        Returns:
            Callable condition object for use with :any:`check_compatibility`
            
        Examples:
            'have_cheese' should be True::
            
                CheeseShop.encourage('have_cheese', True)
             
            'have_cheese' should be set to any value::
                
                CheeseShop.encourage('have_cheese')
            
            The value of 'have_cheese' will be checked for correctness by 'cheese_callback'::
            
                CheeseShop.encourage('have_cheese', cheese_callback)
        """

        def attr_undefined(lhs, lhs_attr, lhs_value, rhs, rhs_attr):
            lhs_name = lhs.name.lower()
            rhs_name = rhs.name.lower()
            LOGGER.warning(
                "%s = %s in %s recommends %s be defined in %s but it is undefined",
                lhs_attr, lhs_value, lhs_name, rhs_attr, rhs_name)

        def attr_ne(lhs, lhs_attr, lhs_value, rhs, rhs_attr, checked_value):
            lhs_name = lhs.name.lower()
            rhs_name = rhs.name.lower()
            rhs_value = rhs[rhs_attr]
            LOGGER.warning(
                "%s = %s in %s recommends %s = %s in %s but it is %s",
                lhs_attr, lhs_value, lhs_name, rhs_attr, checked_value,
                rhs_name, rhs_value)

        return cls.construct_condition(args,
                                       attr_undefined=attr_undefined,
                                       attr_ne=attr_ne)

    @classmethod
    def discourage(cls, *args):
        """Constructs a compatibility condition to make recommendations.
        
        The condition will emit warnings messages if the specified attribute is
        defined or equal to the specified value (if given).
        
        Args:
            *args: Corresponds to `args` in :any:`construct_condition`. 
        
        Returns:
            Callable condition object for use with :any:`check_compatibility`
            
        Examples:
            'have_cheese' should not be True::
            
                CheeseShop.discourage('have_cheese', True)
             
            'have_cheese' should not be set to any value::
                
                CheeseShop.discourage('have_cheese')
            
            The value of 'have_cheese' will be checked for correctness by 'cheese_callback'::
            
                CheeseShop.discourage('have_cheese', cheese_callback)
        """

        def attr_defined(lhs, lhs_attr, lhs_value, rhs, rhs_attr):
            lhs_name = lhs.name.lower()
            rhs_name = rhs.name.lower()
            LOGGER.warning("%s = %s in %s recommends %s be undefined in %s",
                           lhs_attr, lhs_value, lhs_name, rhs_attr, rhs_name)

        def attr_eq(lhs, lhs_attr, lhs_value, rhs, rhs_attr, checked_value):
            lhs_name = lhs.name.lower()
            rhs_name = rhs.name.lower()
            LOGGER.warning("%s = %s in %s recommends against %s = %s in %s",
                           lhs_attr, lhs_value, lhs_name, rhs_attr,
                           checked_value, rhs_name)

        return cls.construct_condition(args,
                                       attr_defined=attr_defined,
                                       attr_eq=attr_eq)

    @classmethod
    def exclude(cls, *args):
        """Constructs a compatibility condition to enforce required conditions.
        
        The condition will raise a :any:`IncompatibleRecordError` if the specified attribute is
        defined or equal to the specified value (if given).
        
        Args:
            *args: Corresponds to `args` in :any:`construct_condition`. 
        
        Returns:
            Callable condition object for use with :any:`check_compatibility`
            
        Examples:
            'yellow_cheese' must not be 'American'::
            
                CheeseShop.exclude('yellow_cheese', 'American')
             
            'blue_cheese' must not be set to any value::
                
                CheeseShop.exclude('blue_cheese')
            
            The value of 'have_cheese' will be checked for correctness by 'cheese_callback'::
            
                CheeseShop.exclude('have_cheese', cheese_callback)
        """

        def attr_defined(lhs, lhs_attr, lhs_value, rhs, rhs_attr):
            lhs_name = lhs.name.lower()
            rhs_name = rhs.name.lower()
            raise IncompatibleRecordError(
                f"{lhs_attr} = {lhs_value} in {lhs_name} requires {rhs_attr}"
                f"be undefined in {rhs_name}")

        def attr_eq(lhs, lhs_attr, lhs_value, rhs, rhs_attr, checked_value):
            lhs_name = lhs.name.lower()
            rhs_name = rhs.name.lower()
            raise IncompatibleRecordError(
                f"{lhs_attr} = {lhs_value} in {lhs_name} is incompatible with "
                f"{rhs_attr} = {checked_value} in {rhs_name}")

        return cls.construct_condition(args,
                                       attr_defined=attr_defined,
                                       attr_eq=attr_eq)

    def check_compatibility(self, rhs):
        """Test this record for compatibility with another record.
        
        Operations combining data from multiple records must know that the records are mutually 
        compatible.  This routine checks the 'compat' property of each attribute (if set) to enforce
        compatibility.  'compat' is a dictionary where the keys are values or callables and the 
        values are tuples of compatibility conditions.  If the attribute with the 'compat' property
        is one of the key values then the conditions are checked.  The general form of 'compat' is::
        
            {
            (value|callable): (condition, [condition, ...]),
            [(value|callable): (condition, [condition, ...]), ...]
            }
            
        Use tuples to join multiple conditions.  If only one condition is needed then you do
        not need to use a tuple.
        
        'value' may either be a literal value (e.g. True or "oranges") or a callable accepting
        one argument and returning either True or False.  The attribute's value is passed to the
        callable to determine if the listed conditions should be checked.  If 'value' is a literal
        then the listed conditions are checked when the attribute's value matches 'value'.     
        
        See :any:`require`, :any:`encourage`, :any:`discourage`, :any:`exclude` for common conditions.
        
        Args:
            rhs (Model): Check compatibility with this data record.
            
        Raises:
            IncompatibleRecordError: The two records are not compatible.

        Examples:

            Suppose we have this data:
            ::
            
                Programmer.attributes = {
                    'hungry': {
                        'type': 'boolean',
                        'compat': {True: (CheeseShop.require('have_cheese', True),
                                          CheeseShop.encourage('chedder', 'Wisconsin'),
                                          ProgramManager.discourage('holding_long_meeting', True),
                                          Roommate.exclude('steals_food', True)}
                    }
                }

                bob = Programmer({'hungry': True})
                world_o_cheese = CheeseShop({'have_cheese': False, 'chedder': 'Wisconsin'})
                cheese_wizzard = CheeseShop({'have_cheese': True, 'chedder': 'California'})
                louis = ProgramManager({'holding_long_meeting': True})
                keith = Roommate({'steals_food': True})
                
            These expressions raise :any:`IncompatibleRecordError`::
            
                bob.check_compatibility(world_o_cheese)   # Because have_cheese == False
                bob.check_compatibility(keith)            # Because steals_food == True
            
            These expressions generate warning messages::
            
                bob.check_compatibility(cheese_wizzard)   # Because chedder != Wisconsin
                bob.check_compatibility(louis)            # Because holding_long_meeting == True
                
            If ``bob['hungry'] == False`` or if the 'hungry' attribute were not set then all 
            the above expressions do nothing.
        """
        as_tuple = lambda x: x if isinstance(x, tuple) else (x, )
        for attr, props in self.attributes.items():
            try:
                compat = props['compat']
            except KeyError:
                continue
            try:
                attr_value = self[attr]
            except KeyError:
                continue
            for value, conditions in compat.items():
                if (callable(value)
                        and value(attr_value)) or attr_value == value:
                    for condition in as_tuple(conditions):
                        condition(self, attr, attr_value, rhs)

    @classmethod
    def filter_arguments(cls, args):
        from e4s_cl.cli.arguments import ArgumentsNamespace
        filtered = dict(item for item in vars(args).items()
                        if item[0] in cls.attributes)
        return ArgumentsNamespace(**filtered)
