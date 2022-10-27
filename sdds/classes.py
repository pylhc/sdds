"""
Classes
-------

This module holds classes to handle different namelist commands in an SDDS file.
Implementation are based on documentation at:
https://ops.aps.anl.gov/manuals/SDDStoolkit/SDDStoolkitsu2.html
"""
from typing import Any, Tuple, List, Iterator, Optional, Dict, ClassVar
from dataclasses import dataclass, fields
import logging

LOGGER = logging.getLogger(__name__)


##############################################################################
#  Types and Encoding
##############################################################################

ENCODING = "utf-8"
ENCODING_LEN = 1

ENDIAN = {'little': '<', 'big': '>'}

NUMTYPES = {"float": "f", "double": "d", "short": "i2",
            "long": "i4", "llong": "i8", "char": "i1", "boolean": "i1",
            "string": "s"}
NUMTYPES_SIZES = {"float": 4, "double": 8, "short": 2,
                  "long": 4, "llong": 8, "char": 1, "boolean": 1}
NUMTYPES_CAST = {"float": float, "double": float, "short": int,
                 "long": int, "llong": int, "char": str, "boolean": int}


def get_dtype_str(type_: str, endianness: str = 'big', length: int = None):
    if length is None:
        length = ''
    return f"{ENDIAN[endianness]}{length}{NUMTYPES[type_]}"


##############################################################################
#  Classes
##############################################################################

@dataclass
class Description:
    """
    Description (&description) command container.

    This optional command describes the data set in terms of two strings. The first, text,
    is an informal description that is intended principally for human consumption. The second,
    contents, is intended to formally specify the type of data stored in a data set. Most
    frequently, the contents field is used to record the name of the program that created or most
    recently modified the file.
    
    Fields:
        text (str): Optional. Informal description intended for humans.
        contents (str): Optional. Formal specification of the type of data stored in a data set.
    """
    text: Optional[str] = None
    contents: Optional[str] = None
    TAG: ClassVar[str] = "&description"

    def __repr__(self):
        return f"<SDDS Description Container>"


@dataclass
class Include:
    """
    Include (&include) command container.

    This optional command directs that SDDS header lines be read from the file named by the
    filename field. These commands may be nested.

    Fields:
        filename (str): Name of the file to be read containing header lines.
    """
    filename: str

    def __repr__(self):
        return f"<SDDS Include Container>"

    def __str__(self):
        return f"Include: {self.filename:s}"


@dataclass
class Definition:
    """
    Abstract class for the common behaviour of the data definition commands.


    The Column, Array and Parameter definitions inherit from this class. They can be created just by
    passing name and type and optionally more parameters that depend on the actual definition type.

    Fields:
        name (str): Name of the data.
        type (str): Type of the data.
                    One of "short", "long", "float", "double", "character", or "string".
        symbol (str): Optional. Allows specification of a symbol to represent the parameter;
                      it may contain escape sequences, for example,
                      to produce Greek or mathematical characters.
        units (str): Optional. Allows specification of the units of the parameter.
        description (str): Optional.  Provides for an informal description of the parameter.
        format (str): Optional. Specification of the print format string to be used to print the data
                      (e.g. for ASCII in SDDS or other formats). NOT IMPLEMENTED!

    """
    name: str
    type: str
    symbol: Optional[str] = None
    units: Optional[str] = None
    description: Optional[str] = None
    format: Optional[str] = None

    def __post_init__(self):
        # Fix types (probably strings from reading files) by using the type-hints
        # this only works for native types, not the ones from typing.
        for field in fields(self):
            value = getattr(self, field.name)
            hinted_type = field.type
            if hasattr(hinted_type, "__args__"):  # For the Optional[...] types
                if value is None:
                    continue

                if isinstance(value, str) and value.lower() == "none":
                    # The key should have been skipped when writing, but to be safe
                    LOGGER.debug(f"'None' found in {field.name}.")
                    setattr(self, field.name, None)
                    continue

                # find the proper type from type-hint:
                hinted_type = next(t for t in hinted_type.__args__
                                   if not isinstance(t, type(None)))

            if isinstance(value, hinted_type):
                # all is fine
                continue

            LOGGER.debug(f"converting {field.name}: "
                         f"{type(value).__name__} -> {hinted_type.__name__}")
            setattr(self, field.name, hinted_type(value))

    def get_key_value_string(self) -> str:
        """ Return a string with comma separated key=value pairs.
            Hint: `ClassVars` (like ``TAG``) are ignored in `fields`.
        """
        field_values = {field.name: getattr(self, field.name) for field in fields(self)}
        return ", ".join([f"{key}={value}" for key, value in field_values.items() if value is not None])

    def __repr__(self):
        return f"<SDDS {self.__class__.__name__} '{self.name}'>"

    def __str__(self):
        return f"<{self.__class__.__name__} ({getattr(self, 'TAG', 'no tag')})> {self.get_key_value_string()}"


@dataclass
class Column(Definition):
    """
    Column (&column) command container, a data definition.

    This optional command defines a column that will appear in the tabular data section of each
    data page.
    """
    TAG: ClassVar[str] = "&column"


@dataclass
class Parameter(Definition):
    """
    Parameter (&parameter) command container, a data definition.

    This optional command defines a parameter that will appear along with the tabular data
    section of each data page.

    Fields:
        fixed_value (str): Optional. Allows specification of a constant value for a given parameter.
                           This value will not change from data page to data page,
                           and is not specified along with non-fixed parameters or tabular data.
                           This feature is for convenience only;
                           the parameter thus defined is treated like any other.
    """
    TAG: ClassVar[str] = "&parameter"
    fixed_value: Optional[str] = None


@dataclass
class Array(Definition):
    """
    Array (&array) command container, a data definition.

    This optional command defines an array that will appear along with the tabular data section
    of each data page.

    Fields:
        field_length (int): Optional. Length of the field (Not sure, actually. jdilly2022).
        group_name (int): Optional. Allows specification of a string giving the
                          name of the array group to which the array belongs;
                          such strings may be defined by the user
                          to indicate that different arrays are related
                          (e.g., have the same dimensions, or parallel elements).
        dimensions (int): Optional. Gives the number of dimensions in the array.
                          If not given, defaults to ``1`` upon reading.
    """
    TAG: ClassVar[str] = "&array"
    field_length: Optional[int] = None
    group_name: Optional[str] = None
    dimensions: Optional[int] = None


@dataclass
class Data:
    """
    Data (&data) command container.

    This command is optional unless parameter commands without fixed_value fields,
    array commands, or column commands have been given.

    Fields:
        mode (str): File/Data mode. Either “binary” or "ascii".
    """
    mode: str
    TAG: ClassVar[str] = "&data"

    def __repr__(self):
        return f"<SDDS {self.mode} Data Container>"


class SddsFile:
    """
    Holds the contents of the SDDS file as a pair of dictionaries.

    The first dictionary "definitions" has the form: **name (str) -> Definition**, containing an
    object of each field in the SDDS file (of type `Parameter`, `Array` or `Column`). The "values"
    dictionary has the form: **name (str) -> value**. To access them: ``sdds_file = SddsFile(...)``.

    .. code-block:: python

        def_ = sdds_file.definitions["name"]
        val = sdds_file.values["name"]
        # The definitions and values can also be accessed like:
        def_, val = sdds_file["name"]

    Args:
        version (str): Always needs to be "SDDS1"!
        description (Description): Optional. Description Tag.
        definitions_list (list[Definition]): List of definitions objects,
                                             describing the data.
        values_list (list[Any]): List of values for the SDDS data.
                                 Same lengths as definitions.

    Fields:
        version (str): Always needs to be "SDDS1"!
        description (Description): Optional. Description Tag.
        definitions (dict[str, Definition]): Definitions of the data, mapped to their name.
        values (dict[str, Any]): Values of the data, mapped to their name.

    """
    version: str  # This should always be "SDDS1"
    description: Optional[Description]
    definitions: Dict[str, Definition]
    values: Dict[str, Any]

    def __init__(self, version: str, description: Optional[Description],
                 definitions_list: List[Definition],
                 values_list: List[Any]) -> None:
        self.version = version

        name_list = [definition.name for definition in definitions_list]
        if len(name_list) != len(set(name_list)):
            raise ValueError("Duplicated name entries found")

        self.description = description
        self.definitions = {definition.name: definition for definition in definitions_list}
        self.values = {definition.name: value for definition, value
                       in zip(definitions_list, values_list)}

    def __getitem__(self, name: str) -> Tuple[Definition, Any]:
        return self.definitions[name], self.values[name]

    def __iter__(self) -> Iterator[Tuple[Definition, Any]]:
        for def_name in self.definitions:
            yield self[def_name]

    def __repr__(self):
        return f"<SDDS-File Object>"

    def __str__(self):
        return f"SDDS-File ({self.version})"  # TODO make something nice
