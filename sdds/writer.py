"""
Writer
------

This module contains the writing functionality of ``sdds``.
It provides a high-level function to write SDDS files in different formats, and a series of helpers.
"""
import itertools
import pathlib
import struct
from typing import IO, List, Union, Iterable, Tuple, Any

import numpy as np

from sdds.classes import (
    SddsFile,
    Column,
    Parameter,
    Definition,
    Array,
    Data,
    Description,
    ENCODING,
    get_dtype_str,
    NUMTYPES_ascii,
)


def write_sdds(sdds_file: SddsFile, output_path: Union[pathlib.Path, str], mode: str = None) -> None:
    """
    Writes SddsFile object into ``output_path``.
    The byteorder will be big-endian, independent of the byteorder of the current machine.

    Args:
        sdds_file: `SddsFile` object to write
        output_path (Union[pathlib.Path, str]): `Path` object to the output SDDS file. Can be
            a `string`, in which case it will be cast to a `Path` object.
        mode: Mode to write sdds-file in. If given, overrides the mode in sdds_file.
              If neither is given, defaults to "binary".
    """
    output_path = pathlib.Path(output_path)
    sdds_file.mode = mode if mode is not None else getattr(sdds_file, "mode", "binary")  # argument > sdds.mode > "binary"

    with output_path.open("wb") as outbytes:
        names = _write_header(sdds_file, outbytes)
        if sdds_file.mode == "binary":
            _write_data(names, sdds_file, outbytes)
        elif sdds_file.mode == "ascii":
            _write_ascii_data(names, sdds_file, outbytes)


def _write_header(sdds_file: SddsFile, outbytes: IO[bytes]) -> List[str]:
    outbytes.write("SDDS1\n".encode(ENCODING))

    if sdds_file.mode == "binary":
        outbytes.write("!# big-endian\n".encode(ENCODING))

    names = []
    if sdds_file.description is not None:
        outbytes.write(_sdds_def_as_str(sdds_file.description).encode(ENCODING))
    for def_name in sdds_file.definitions:
        names.append(def_name)
        definition = sdds_file.definitions[def_name]
        outbytes.write(_sdds_def_as_str(definition).encode(ENCODING))

    outbytes.write(f"&data mode={sdds_file.mode}, &end\n".encode(ENCODING))
    return names


def _sdds_def_as_str(definition: Union[Description, Definition, Data]) -> str:
    start = definition.TAG + " "
    things = ", ".join(
        [
            f"{key}={definition.__dict__[key]}"
            for key in definition.__dict__
            if "__" not in key
        ]
    )
    end = " &end\n"
    return start + things + end


def _get_row_count(sdds_file, names):
    # get number of columns
    if sdds_file.npages > 1:
        col_data = [
            [sdds_file[name][0], sdds_file.values[name][0]]
            for name in names
            if isinstance(sdds_file.definitions[name], Column)
        ]
    else:
        col_data = [
            sdds_file[name]
            for name in names
            if isinstance(sdds_file.definitions[name], Column)
        ]
    # write row count to file
    if len(col_data) > 0:
        col_vals = [item[1] for item in col_data]
        nrow = len(col_vals[0])
    else:
        nrow = 0

    return nrow


def _write_data(names: List[str], sdds_file: SddsFile, outbytes: IO[bytes]) -> None:

    nrow = _get_row_count(sdds_file, names)
    if sdds_file.npages > 1:
        for npage in range(sdds_file.npages):  # write pages
            # write row count
            outbytes.write(np.array(nrow, dtype=get_dtype_str("long")).tobytes())

            _write_parameters(
                (
                    (sdds_file[name][0], sdds_file[name][1][npage])
                    for name in names
                    if isinstance(sdds_file.definitions[name], Parameter)
                ),
                outbytes,
            )
            _write_arrays(
                (
                    (sdds_file[name][0], sdds_file[name][1][npage])
                    for name in names
                    if isinstance(sdds_file.definitions[name], Array)
                ),
                outbytes,
            )
            _write_columns(
                [
                    [sdds_file[name][0], sdds_file.values[name][npage]]
                    for name in names
                    if isinstance(sdds_file.definitions[name], Column)
                ],
                outbytes,
            )
    else:
        # write row count
        outbytes.write(np.array(nrow, dtype=get_dtype_str("long")).tobytes())
        _write_parameters(
            (
                sdds_file[name]
                for name in names
                if isinstance(sdds_file.definitions[name], Parameter)
            ),
            outbytes,
        )
        _write_arrays(
            (
                sdds_file[name]
                for name in names
                if isinstance(sdds_file.definitions[name], Array)
            ),
            outbytes,
        )
        _write_columns(
            [
                sdds_file[name]
                for name in names
                if isinstance(sdds_file.definitions[name], Column)
            ],
            outbytes,
        )


def _write_parameters(param_gen: Iterable[Tuple[Parameter, Any]], outbytes: IO[bytes]):
    for param_def, value in param_gen:
        if param_def.type in ["string"]:  # character will to be displayed by sddsprintout but it is not throwing an error
            _write_string(value, outbytes)
        elif param_def.type in ["char", "character"]:
            outbytes.write(
                struct.pack(
                    get_dtype_str("char", length=len(value)), value.encode(ENCODING)
                )
            )
        else:
            outbytes.write(
                np.array(value, dtype=get_dtype_str(param_def.type)).tobytes()
            )


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
            outbytes.write(
                np.array(value, dtype=get_dtype_str(array_def.type)).tobytes()
            )


# def _write_columns(col_gen: Iterable[Tuple[Column, Any]], outbytes: IO[bytes]):
def _write_columns(col_data, outbytes: IO[bytes]):
    try:
        col_defs = [item[0] for item in col_data]
        col_vals = [item[1] for item in col_data]
        col_vals = list(zip(*col_vals))

        for i in range(len(col_vals)):
            for j in range(len(col_vals[0])):
                col_val = col_vals[i]
                value = col_val[j]
                col_def = col_defs[j]

                print(col_def, value)
                if col_def.type in ["string"]:
                    _write_string(value, outbytes)
                elif col_def.type in ["character", "char"]:
                    outbytes.write(
                        struct.pack(
                            get_dtype_str("char", length=len(value)),
                            value.encode(ENCODING),
                        )
                    )
                else:
                    outbytes.write(
                        np.array(value, dtype=get_dtype_str(col_def.type)).tobytes()
                    )
    except:
        pass


def _write_string(string: str, outbytes: IO[bytes]):
    if len(string) == 1:
        string = string
    outbytes.write(np.array(len(string), dtype=get_dtype_str("long")).tobytes())
    outbytes.write(
        struct.pack(
            get_dtype_str("string", length=len(string)), string.encode(ENCODING)
        )
    )


def _write_ascii_data(names: List[str], sdds_file: SddsFile, outbytes: IO[bytes]) -> None:  # one may can combine write_ascii_data with write_data ...
    """Write sdds file in ASCII."""
    # outbytes.write(np.array(0, dtype=get_dtype_str("long")).tobytes())

    if sdds_file.npages > 1:
        for npage in range(sdds_file.npages):  # write pages
            pagecomment = "! page number %i\n" % (npage + 1)
            outbytes.write(pagecomment.encode(ENCODING))
            _write_ascii_parameters(
                (
                    (sdds_file[name][0], sdds_file[name][1][npage])
                    for name in names
                    if isinstance(sdds_file.definitions[name], Parameter)
                ),
                outbytes,
            )
            _write_ascii_arrays(
                (
                    (sdds_file[name][0], sdds_file[name][1][npage])
                    for name in names
                    if isinstance(sdds_file.definitions[name], Array)
                ),
                outbytes,
            )
            _write_ascii_columns(
                [
                    [sdds_file[name][0], sdds_file.values[name][npage]]
                    for name in names
                    if isinstance(sdds_file.definitions[name], Column)
                ],
                outbytes,
            )
    else:
        _write_ascii_parameters(
            (
                sdds_file[name]
                for name in names
                if isinstance(sdds_file.definitions[name], Parameter)
            ),
            outbytes,
        )
        _write_ascii_arrays(
            (
                sdds_file[name]
                for name in names
                if isinstance(sdds_file.definitions[name], Array)
            ),
            outbytes,
        )
        _write_ascii_columns(
            [
                sdds_file[name]
                for name in names
                if isinstance(sdds_file.definitions[name], Column)
            ],
            outbytes,
        )


def _write_ascii_parameters(
    param_gen: Iterable[Tuple[Parameter, Any]], outbytes: IO[bytes]
):
    for param_def, value in param_gen:
        tstr = NUMTYPES_ascii[param_def.type] % (value)
        tstr = tstr + "\n"
        outbytes.write(tstr.encode(ENCODING))


def _write_ascii_arrays(array_gen: Iterable[Tuple[Array, Any]], outbytes: IO[bytes]):
    def get_dimensions_from_array(value):
        # Return the number of items per dimension
        # For an array a[n][m], returns [n, m]
        if isinstance(value, np.ndarray) or isinstance(value, list):
            return [len(value)] + get_dimensions_from_array(value[0])
        return []

    for array_def, value in array_gen:
        # Number of items per dimensions need to be written before the data
        elements_per_dim = get_dimensions_from_array(value)
        shape = np.array(elements_per_dim)
        tstr = ""
        for cell in shape:
            tstr = tstr + " " + NUMTYPES_ascii["short"] % (cell)
        tstr = tstr + "\n"
        outbytes.write(tstr.encode(ENCODING))
        # write array data
        for idx in itertools.product(*[range(s) for s in shape]):
            val = value[idx]
            outbytes.write(
                str(" " + NUMTYPES_ascii[array_def.type] % (val)).encode(ENCODING)
            )
        tstr = "\n"
        outbytes.write(tstr.encode(ENCODING))


def _write_ascii_columns(col_data, outbytes: IO[bytes]):

    try:

        col_defs = [item[0] for item in col_data]
        col_vals = [item[1] for item in col_data]

        nrow = len(col_vals[0])
        col_vals = list(zip(*col_vals))

        tstr = " %i\n" % nrow
        outbytes.write(tstr.encode(ENCODING))

        for i in range(len(col_vals)):
            for j in range(len(col_vals[0])):
                col_val = col_vals[i]
                outbytes.write(
                    str(" " + NUMTYPES_ascii[col_defs[j].type] % (col_val[j])).encode(
                        ENCODING
                    )
                )
            tstr = "\n"
            outbytes.write(tstr.encode(ENCODING))

    except:
        pass
