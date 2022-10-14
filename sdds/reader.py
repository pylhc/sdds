"""
Reader
------

This module contains the reading functionality of ``sdds``.
It provides a high-level function to read SDDS files in different formats, and a series of helpers.
"""
import pathlib
import struct
import sys
from typing import IO, Any, List, Optional, Generator, Dict, Union, Tuple, Callable, Type

import numpy as np

from sdds.classes import (SddsFile, Column, Parameter, Definition, Array, Data, Description,
                          ENCODING, NUMTYPES_CAST, NUMTYPES_SIZES, get_dtype_str)


def read_sdds(file_path: Union[pathlib.Path, str], endianness: str = None) -> SddsFile:
    """
    Reads SDDS file from the specified ``file_path``.

    Args:
        file_path (Union[pathlib.Path, str]): `Path` object to the input SDDS file. Can be a
            `string`, in which case it will be cast to a `Path` object.
        endianness (str): Endianness of the file. Either 'big' or 'little'.
                          If not given, the endianness is either extracted from
                          the comments in the header of the file (if present)
                          or determined by the machine you are running on.
                          Binary files written by this package are all big-endian,
                          and contain a comment in the file.

    Returns:
        An `SddsFile` object containing the loaded data.
    """
    file_path = pathlib.Path(file_path)
    with file_path.open("rb") as inbytes:
        if endianness is None:
            endianness = _get_endianness(inbytes)
        version, definition_list, description, data = _read_header(inbytes)
        data_list = _read_data(data, definition_list, inbytes, endianness)

        return SddsFile(version, description, definition_list, data_list)


##############################################################################
# Common reading of header and data.
##############################################################################

def _read_header(inbytes: IO[bytes]) -> Tuple[str, List[Definition], Optional[Description], Data]:
    word_gen = _gen_words(inbytes)
    version = next(word_gen)  # First token is the SDDS version
    assert version == "SDDS1",\
        "This module is compatible with SDDS v1 only... are there really other versions?"
    definitions: List[Definition] = []
    description: Optional[Description] = None
    data: Optional[Data] = None
    for word in word_gen:
        def_dict: Dict[str, str] = _get_def_as_dict(word_gen)
        if word in (Column.TAG, Parameter.TAG, Array.TAG):
            definitions.append({
                Column.TAG: Column,
                Parameter.TAG: Parameter,
                Array.TAG: Array}[word](name=def_dict.pop("name"),
                                        type=def_dict.pop("type"),
                                        **def_dict))
            continue
        if word == Description.TAG:
            if description is not None:
                raise ValueError("Two &description tags found.")
            description = Description(**def_dict)
            continue
        if word == "&include":
            # TODO: This should be easy but I will not support it for now.
            raise NotImplementedError
        if word == Data.TAG:
            data = Data(mode=def_dict.pop("mode"))
            break
        raise ValueError(f"Unknown token: {word} encountered.")
    if data is None:
        raise ValueError("Found end of file while looking for &data tag.")
    definitions = _sort_definitions(definitions)
    return version, definitions, description, data


def _sort_definitions(orig_defs: List[Definition]) -> List[Definition]:
    """
    Sorts the definitions in the parameter, array, column order.
    According to the specification, parameters appear first in data pages then arrays
    and then columns. Inside each group they follow the order of appearance in the header.
    """
    definitions: List[Definition] = [definition for definition in orig_defs
                                     if isinstance(definition, Parameter)]
    definitions.extend([definition for definition in orig_defs if isinstance(definition, Array)])
    definitions.extend([definition for definition in orig_defs if isinstance(definition, Column)])
    return definitions


def _read_data(data: Data, definitions: List[Definition], inbytes: IO[bytes], endianness: str) -> List[Any]:
    if data.mode == "binary":
        return _read_data_binary(definitions, inbytes, endianness)
    elif data.mode == "ascii":
        return _read_data_ascii(definitions, inbytes)

    raise ValueError(f"Unsupported data mode {data.mode}.")


##############################################################################
# Binary data reading
##############################################################################

def _read_data_binary(definitions: List[Definition], inbytes: IO[bytes], endianness: str) -> List[Any]:
    row_count: int = _read_bin_int(inbytes, endianness)  # First int in bin data
    functs_dict: Dict[Type[Definition], Callable] = {
        Parameter: _read_bin_param,
        Column: lambda x, y, z: _read_bin_column(x, y, z, row_count),
        Array: _read_bin_array
    }
    return [functs_dict[definition.__class__](inbytes, definition, endianness) for definition in definitions]


def _read_bin_param(inbytes: IO[bytes], definition: Parameter, endianness: str) -> Union[int, float, str]:
    try:
        if definition.fixed_value is not None:
            if definition.type == "string":
                return definition.fixed_value
            return NUMTYPES_CAST[definition.type](definition.fixed_value)
    except AttributeError:
        pass
    if definition.type == "string":
        str_len: int = _read_bin_int(inbytes, endianness)
        return _read_string(inbytes, str_len, endianness)
    return NUMTYPES_CAST[definition.type](
        _read_bin_numeric(inbytes, definition.type, 1, endianness)
    )


def _read_bin_column(inbytes: IO[bytes], definition: Column, endianness: str, row_count: int):
    # TODO: This columns things might be interesting to implement.
    raise NotImplementedError("")


def _read_bin_array(inbytes: IO[bytes], definition: Array, endianness: str) -> Any:
    dims, total_len = _read_bin_array_len(inbytes, definition.dimensions, endianness)

    if definition.type == "string":
        len_type = {"u1": "char", "i2": "short"}.get(
            getattr(definition, "modifier", None), "long"
        )
        str_array = []
        for _ in range(total_len):
            str_len = int(_read_bin_numeric(inbytes, len_type, 1, endianness))
            str_array.append(_read_string(inbytes, str_len, endianness))
        return str_array

    data = _read_bin_numeric(inbytes, definition.type, total_len, endianness)
    return data.reshape(dims)


def _read_bin_array_len(inbytes: IO[bytes], num_dims: Optional[int], endianness: str) -> Tuple[List[int], int]:
    if num_dims is None:
        num_dims = 1

    dims = [_read_bin_int(inbytes, endianness) for _ in range(num_dims)]
    return dims, int(np.prod(dims))


def _read_bin_numeric(inbytes: IO[bytes], type_: str, count: int, endianness: str) -> Any:
    return np.frombuffer(inbytes.read(count * NUMTYPES_SIZES[type_]),
                         dtype=np.dtype(get_dtype_str(type_, endianness)))


def _read_bin_int(inbytes: IO[bytes], endianness: str) -> int:
    return int(_read_bin_numeric(inbytes, "long", 1, endianness))


def _read_string(inbytes: IO[bytes], str_len: int, endianness: str) -> str:
    str_dtype = get_dtype_str("string", endianness, length=str_len)
    packed_str = inbytes.read(str_len)
    return struct.unpack(str_dtype, packed_str)[0].decode(ENCODING)


##############################################################################
# ASCII data reading
##############################################################################

def _read_data_ascii(definitions: List[Definition], inbytes: IO[bytes]) -> List[Any]:
    def _ascii_generator(ascii_text):
        for line in ascii_text:
            yield line

    # Convert bytes to ASCII, separate by lines and remove comments
    ascii_text = [chr(r) for r in inbytes.read()]
    ascii_text = ''.join(ascii_text).split('\n')
    ascii_text = [line for line in ascii_text if not line.startswith('!')]

    # Get the generator for the text
    ascii_gen = _ascii_generator(ascii_text)

    # Dict of function to call for each type of tag: array, parameter
    functs_dict = {Parameter: _read_ascii_parameter,
                   Array: _read_ascii_array
                   }

    # Iterate through every parameters and arrays in the file
    data = []
    for definition in definitions:
        def_tag = definition.__class__

        # Call the function handling the tag we're on
        # Change the current line according to the tag and dimensions
        value = functs_dict[def_tag](ascii_gen, definition)
        data.append(value)

    return data


def _read_ascii_parameter(ascii_gen: Generator[str, None, None],
                          definition: Parameter) -> Union[str, int, float]:

    # Check if we got fixed values, no need to read a line if that's the case
    if definition.fixed_value is not None:
        if definition.type == "string":
            return definition.fixed_value
        if definition.type in NUMTYPES_CAST:
            return NUMTYPES_CAST[definition.type](definition.fixed_value)

    # No fixed value -> read a line
    # Strings can be returned without cast
    if definition.type == "string":
        return next(ascii_gen)

    # For other types, a cast is needed
    if definition.type in NUMTYPES_CAST:
        return NUMTYPES_CAST[definition.type](next(ascii_gen))

    raise TypeError(f"Type {definition.type} for Parameter unsupported")


def _read_ascii_array(ascii_gen: Generator[str, None, None],
                      definition: Array) -> np.ndarray:

    # Get the number of elements per dimension
    dimensions = next(ascii_gen).split()
    dimensions = np.array(dimensions, dtype="int")

    # Get all the data given by the dimensions
    data = []
    while len(data) != np.prod(dimensions):
        # The values on each line are split by a space
        data += next(ascii_gen).strip().split(' ')

    # Cast every object to the correct type
    if definition.type != 'string':
        data = list(map(NUMTYPES_CAST[definition.type], data))

    # Convert to np.array so that it can be reshaped to reflect the dimensions
    data = np.array(data)
    data = data.reshape(dimensions)

    return data


##############################################################################
# Helper generators to consume the input bytes
##############################################################################

def _get_endianness(inbytes: IO[bytes]) -> str:
    """Tries to determine endianness from file-comments.
    If nothing found, uses machine endianness."""
    endianness = sys.byteorder
    while True:
        line = inbytes.readline().decode(ENCODING)
        if not line:
            break  # break at beginning of binary part
        if line.strip() == "!# big-endian":
            endianness = "big"
            break
        if line.strip() == "!# little-endian":
            endianness = "little"
            break
    inbytes.seek(0)   # return back to beginning of file
    return endianness


def _gen_real_lines(inbytes: IO[bytes]) -> Generator[str, None, None]:
    """No comments and stripped lines."""
    while True:
        line = inbytes.readline().decode(ENCODING)
        if not line:
            return
        if line != "\n" and not line.strip().startswith("!"):
            yield line.strip()


def _gen_words(inbytes: IO[bytes]) -> Generator[str, None, None]:
    for line in _gen_real_lines(inbytes):
        for word in line.split():
            yield word
    return


def _get_def_as_dict(word_gen: Generator[str, None, None]) -> Dict[str, str]:
    raw_str: List[str] = []
    for word in word_gen:
        if word.strip() == "&end":
            recomposed: str = " ".join(raw_str)
            parts = [assign for assign in recomposed.split(",") if assign]
            return {key.strip(): value.strip() for (key, value) in
                    [assign.split("=") for assign in parts]}
        raw_str.append(word.strip())
    raise ValueError("EOF found while looking for &end tag.")
