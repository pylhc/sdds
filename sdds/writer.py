"""
Writer
------

This module contains the writing functionality of ``sdds``.
It provides a high-level function to write SDDS files in different formats, and a series of helpers.
"""
import pathlib
import struct
from dataclasses import fields
from typing import IO, List, Union, Iterable, Tuple, Any
import numpy as np
from sdds.classes import (SddsFile, Column, Parameter, Definition, Array, Data, Description,
                          ENCODING, get_dtype_str)


def write_sdds(sdds_file: SddsFile, output_path: Union[pathlib.Path, str]) -> None:
    """
    Writes SddsFile object into ``output_path``.
    The byteorder will be big-endian, independent of the byteorder of the current machine.

    Args:
        sdds_file: `SddsFile` object to write
        output_path (Union[pathlib.Path, str]): `Path` object to the output SDDS file. Can be
            a `string`, in which case it will be cast to a `Path` object.
    """
    output_path = pathlib.Path(output_path)
    with output_path.open("wb") as outbytes:
        names = _write_header(sdds_file, outbytes)
        _write_data(names, sdds_file, outbytes)


def _write_header(sdds_file: SddsFile, outbytes: IO[bytes]) -> List[str]:
    outbytes.writelines(("SDDS1\n".encode(ENCODING),
                         "!# big-endian\n".encode(ENCODING)))
    names = []
    if sdds_file.description is not None:
        outbytes.write(_sdds_def_as_str(sdds_file.description).encode(ENCODING))
    for def_name in sdds_file.definitions:
        names.append(def_name)
        definition = sdds_file.definitions[def_name]
        outbytes.write(_sdds_def_as_str(definition).encode(ENCODING))
    outbytes.write("&data mode=binary, &end\n".encode(ENCODING))
    return names


def _sdds_def_as_str(definition: Union[Description, Definition, Data]) -> str:
    return f"{definition.TAG} {definition.get_key_value_string()} &end\n"


def _write_data(names: List[str], sdds_file: SddsFile, outbytes: IO[bytes]) -> None:
    # row_count:
    outbytes.write(np.array(0, dtype=get_dtype_str("long")).tobytes())
    _write_parameters((sdds_file[name] for name in names
                       if isinstance(sdds_file.definitions[name], Parameter)),
                      outbytes)
    _write_arrays((sdds_file[name] for name in names
                   if isinstance(sdds_file.definitions[name], Array)),
                  outbytes)
    _write_columns((sdds_file[name] for name in names
                    if isinstance(sdds_file.definitions[name], Column)),
                   outbytes)


def _write_parameters(param_gen: Iterable[Tuple[Parameter, Any]], outbytes: IO[bytes]):
    for param_def, value in param_gen:
        if param_def.type == "string":
            _write_string(value, outbytes)
        else:
            outbytes.write(np.array(value, dtype=get_dtype_str(param_def.type)).tobytes())


def _write_arrays(array_gen: Iterable[Tuple[Array, Any]], outbytes: IO[bytes]):
    def get_dimensions_from_array(value):
        # Return the number of items per dimension
        # For an array a[n][m], returns [n, m]
        if isinstance(value, np.ndarray) or isinstance(value, list):
            return [len(value)] + get_dimensions_from_array(value[0])
        return []

    for array_def, value in array_gen:
        # Number of items per dimensions need to be written before the data
        elements_per_dim = get_dimensions_from_array(value)
        long_array = np.array(elements_per_dim, dtype=get_dtype_str("long"))
        outbytes.write(long_array.tobytes())

        if array_def.type == "string":
            for string in value:
                _write_string(string, outbytes)
        else:
            outbytes.write(np.array(value, dtype=get_dtype_str(array_def.type)).tobytes())


def _write_columns(col_gen: Iterable[Tuple[Column, Any]], outbytes: IO[bytes]):
    # TODO: Implement the columns thing.
    pass


def _write_string(string: str, outbytes: IO[bytes]):
    outbytes.write(np.array(len(string), dtype=get_dtype_str("long")).tobytes())
    outbytes.write(struct.pack(get_dtype_str("string", length=len(string)), string.encode(ENCODING)))
