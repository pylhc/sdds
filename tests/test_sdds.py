import io
import os
import pathlib
import struct
import sys
from typing import Dict

import numpy as np
import pytest

from sdds.classes import (
    NUMTYPES,
    Array,
    Column,
    Data,
    Definition,
    Description,
    Include,
    Parameter,
    SddsFile,
    get_dtype_str,
)
from sdds.reader import _gen_words, _get_def_as_dict, _read_data, _read_header, _sort_definitions, gzip_open, read_sdds
from sdds.writer import _sdds_def_as_str, write_sdds

CURRENT_DIR = pathlib.Path(__file__).parent


class TestReadWrite:
    def test_sdds_write_read_pathlib_input(self, _sdds_file_pathlib, tmp_file):
        original = read_sdds(_sdds_file_pathlib)
        write_sdds(original, tmp_file)
        new = read_sdds(tmp_file)
        for definition, value in original:
            new_def, new_val = new[definition.name]
            assert new_def.name == definition.name
            assert new_def.type == definition.type
            assert np.all(value == new_val)

    def test_sdds_write_read_str_input(self, _sdds_file_str, tmp_file):
        original = read_sdds(_sdds_file_str)
        write_sdds(original, tmp_file)
        new = read_sdds(tmp_file)
        for definition, value in original:
            new_def, new_val = new[definition.name]
            assert new_def.name == definition.name
            assert new_def.type == definition.type
            assert np.all(value == new_val)

    def test_empty_array(self, _sdds_file_pathlib, tmp_file):
        original = read_sdds(_sdds_file_pathlib)
        original.values["horPositionsConcentratedAndSorted"] = np.array([])
        write_sdds(original, tmp_file)


class TestReadGzippedFiles:
    def test_sdds_read_gzipped_file_pathlib(self, _sdds_gzipped_file_pathlib, tmp_file):
        original = read_sdds(_sdds_gzipped_file_pathlib, opener=gzip_open)  # type: ignore
        write_sdds(original, tmp_file)
        new = read_sdds(tmp_file)
        for definition, value in original:
            new_def, new_val = new[definition.name]
            assert new_def.name == definition.name
            assert new_def.type == definition.type
            assert np.all(value == new_val)

    def test_sdds_read_gzipped_file_str(self, _sdds_gzipped_file_str, tmp_file):
        original = read_sdds(_sdds_gzipped_file_str, opener=gzip_open)  # type: ignore
        write_sdds(original, tmp_file)
        new = read_sdds(tmp_file)
        for definition, value in original:
            new_def, new_val = new[definition.name]
            assert new_def.name == definition.name
            assert new_def.type == definition.type
            assert np.all(value == new_val)


class TestEndianness:
    def test_sdds_read_little_endian(self, _sdds_file_little_endian):
        read_sdds(_sdds_file_little_endian)

    def test_sdds_read_big_endian(self, _sdds_file_pathlib):
        read_sdds(_sdds_file_pathlib)

    def test_sdds_read_big_endian_as_little_endian(self, _sdds_file_pathlib):
        with pytest.raises(ValueError) as e:
            read_sdds(_sdds_file_pathlib, endianness="little")
        assert "buffer size" in str(e)

    def test_sdds_read_little_endian_as_big_endian(self, _sdds_file_little_endian):
        with pytest.raises(struct.error) as e:
            read_sdds(_sdds_file_little_endian, endianness="big")
        assert "buffer" in str(e)

    def test_sdds_write_read_write_little_endian(self, _sdds_file_little_endian, tmp_file):
        original = read_sdds(_sdds_file_little_endian)
        write_sdds(original, tmp_file)  # written as big-endian
        new = read_sdds(tmp_file)  # read as big-endian
        for definition, value in original:
            new_def, new_val = new[definition.name]
            assert new_def.name == definition.name
            assert new_def.type == definition.type
            assert np.all(value == new_val)


class TestReadFunctions:
    def test_read_word(self, _sdds_file_str):
        test_str = b"""   test1\ntest2 test3,\ttest4
        """
        word_gen = _gen_words(io.BytesIO(test_str))
        assert next(word_gen) == "test1"
        assert next(word_gen) == "test2"
        assert next(word_gen) == "test3,"
        assert next(word_gen) == "test4"

    def test_read_no_more(self):
        test_str = b""
        with pytest.raises(StopIteration):
            next(_gen_words(io.BytesIO(test_str)))

    def test_read_header(self):
        test_head = b"""
        SDDS1
        !# big-endian
        &parameter name=acqStamp, type=double, &end
        &parameter name=nbOfCapTurns, type=long, &end
        &array name=horPositionsConcentratedAndSorted, type=float, &end
        &array
            name=verBunchId,
            type=long,
            field_length=3,
        &end
        &data mode=binary, &end
        """
        test_data = {
            "acqStamp": "double",
            "nbOfCapTurns": "long",
            "horPositionsConcentratedAndSorted": "float",
            "verBunchId": "long",
        }
        version, definitions, _, data = _read_header(io.BytesIO(test_head))
        assert version == "SDDS1"
        assert data.mode == "binary"
        for definition in definitions:
            assert definition.type == test_data[definition.name]

    def test_read_header_optionals(self):
        # build
        to_check = {
            "Step": {"type": "long", "class": "Parameter"},
            "SVNVersion": {
                "type": "string",
                "class": "Parameter",
                "description": '"SVN version number"',
                "fixed_value": "28096M",
            },
            "ElementName": {"type": "string", "class": "Column"},
            "s": {"type": "double", "units": "m", "class": "Column"},
            "ElementType": {"type": "string", "class": "Column"},
            "ElementOccurence": {"type": "long", "class": "Column"},
            "deltaPositiveFound": {"type": "short", "class": "Column"},
            "deltaPositive": {
                "type": "double",
                "symbol": '"$gd$R$bpos$n"',
                "class": "Column",
            },
        }

        test_head = (
            "SDDS1\n"
            "!# little-endian\n"
            '&description text="Momentum aperture search", contents="momentum aperture", &end\n'
            + _header_from_dict(to_check)
            + "&data mode=binary, &end"
        ).encode("ascii")

        # read
        # returns version, definitions, description, data
        _, definitions, _, _ = _read_header(io.BytesIO(test_head))

        # check
        for entry in definitions:
            check_dict = to_check[entry.name]
            assert entry.__class__.__name__ == check_dict.pop("class")
            for key, value in check_dict.items():
                assert getattr(entry, key) == value


def test_def_as_dict():
    test_str = b"test1=value1,  test2= value2, \n" b"test3=value3, &end"
    word_gen = _gen_words(io.BytesIO(test_str))
    def_dict = _get_def_as_dict(word_gen)
    assert def_dict["test1"] == "value1"
    assert def_dict["test2"] == "value2"
    assert def_dict["test3"] == "value3"


def test_sort_defs():
    param1 = Parameter(name="param1", type="long")
    param2 = Parameter(name="param2", type="long")
    array1 = Array(name="array1", type="long")
    array2 = Array(name="array2", type="long")
    col1 = Column(name="col1", type="long")
    col2 = Column(name="col2", type="long")
    unsorted = [array1, col1, param1, param2, array2, col2]
    sorted_ = [param1, param2, array1, array2, col1, col2]
    assert sorted_ == _sort_definitions(unsorted)


class TestAscii:
    def template_ascii_read_write_read(self, filepath, output):
        original = read_sdds(filepath)
        write_sdds(original, output)
        new = read_sdds(output)

        for definition, value in original:
            new_def, new_val = new[definition.name]
            assert new_def.name == definition.name
            assert new_def.type == definition.type

            if not isinstance(value, np.ndarray):
                values_equal = np.isclose(value, new_val, atol=0.0001)
            elif isinstance(value[0], np.str_):
                values_equal = all([a == b for a, b in zip(value, new_val)])
            else:
                values_equal = np.isclose(value, new_val, atol=0.0001).all()

            assert values_equal

    def test_sdds_write_read_ascii_1_dim(self, _sdds_file_lei1, tmp_file):
        self.template_ascii_read_write_read(_sdds_file_lei1, tmp_file)

    def test_sdds_write_read_ascii_2_dim(self, _sdds_file_lei2, tmp_file):
        self.template_ascii_read_write_read(_sdds_file_lei2, tmp_file)

    def test_sdds_write_ascii(self):
        sdds_file = b"""SDDS1
&array name=arrayOne, type=float, dimensions=1, &end
&array name=arrayTwo, type=float, dimensions=2, &end
&data mode=ascii, &end
10
10 9 8 7 6 5 4 3 2 1
5 5
25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9 8
7 6 5 4 3
2 1
"""
        sdds_io = io.BytesIO(sdds_file)
        version, definitions, _, data = _read_header(sdds_io)
        data_list = _read_data(data, definitions, sdds_io, endianness=sys.byteorder)

        assert version == "SDDS1"
        assert len(definitions) == 2
        assert definitions[0].dimensions == 1  # type: ignore
        assert definitions[1].dimensions == 2  # type: ignore

        assert (data_list[0] == np.arange(10, 0, -1)).all()

        assert (data_list[1][0] == np.arange(25, 20, -1)).all()
        assert (data_list[1][1] == np.arange(20, 15, -1)).all()
        assert (data_list[1][2] == np.arange(15, 10, -1)).all()
        assert (data_list[1][3] == np.arange(10, 5, -1)).all()
        assert (data_list[1][4] == np.arange(5, 0, -1)).all()


class TestClasses:
    def test_duplicated_entries(self):
        with pytest.raises(ValueError) as e:
            SddsFile(
                version="SDDS1",
                description=None,
                definitions_list=[
                    Parameter(name="test", type="int"),
                    Parameter(name="test", type="str"),
                ],
                values_list=[1, "hello"],
            )
        assert "Duplicated" in str(e)

    def test_string_and_repr(self):
        sdds = SddsFile(version="SDDS1", description=None, definitions_list=[], values_list=[])
        assert "SDDS-File" in repr(sdds)
        assert "SDDS-File" in str(sdds)

        definition = Definition(name="mydef", type="mytype")
        assert "Definition" in repr(definition)
        assert "mydef" in repr(definition)
        assert "Definition" in str(definition)
        assert "mydef" in str(definition)
        assert "mytype" in str(definition)
        assert "no tag" in str(definition)

        array = Array(name="mydef", type="mytype")
        assert "Array" in repr(array)
        assert "Array" in str(array)
        assert "&array" in str(array)

        data = Data(mode="binary")
        assert "binary" in repr(data)
        assert "binary" in str(data)

        include = Include(filename="myfile")
        assert "Include" in repr(include)
        assert "Include" in str(include)
        assert "myfile" in str(include)

        description = Description()
        assert "Description" in repr(description)
        assert "Description" in str(description)

    def test_get_dtype(self):
        assert ">" in get_dtype_str("float", endianness="big")
        assert ">" in get_dtype_str("float")  # important for reading
        assert "<" not in get_dtype_str("float")  # important for reading
        assert "<" in get_dtype_str("float", endianness="little")
        assert "16" in get_dtype_str("string", length=16)

        for name, format_ in NUMTYPES.items():
            assert get_dtype_str(name).endswith(format_)


# ----- Helpers ----- #


def _write_read_header():
    original = Parameter(name="param1", type="str")
    encoded = _sdds_def_as_str(original).encode("utf-8")
    word_gen = _gen_words(io.BytesIO(encoded))
    def_dict = _get_def_as_dict(word_gen)
    assert def_dict["name"] == original.name
    assert def_dict["type"] == original.type


def _header_from_dict(d: Dict[str, Dict[str, str]]) -> str:
    """Build a quick header from given dict."""
    d = {k: v.copy() for k, v in d.items()}
    return (
        ", &end\n".join(  # join lines
            f"&{v.pop('class').lower()} name={k}, type={v.pop('type')}"
            + (", " + ", ".join(f"{vk}={vv}" for vk, vv in v.items()) if v else "")
            for k, v in d.items()
        )
        + ", &end\n"
    )


# ----- Fixtures ----- #


@pytest.fixture()
def _sdds_file_pathlib() -> pathlib.Path:
    return CURRENT_DIR / "inputs" / "test_file.sdds"


@pytest.fixture()
def _sdds_file_str() -> str:
    return os.path.join(os.path.dirname(__file__), "inputs", "test_file.sdds")


@pytest.fixture()
def _sdds_gzipped_file_pathlib() -> pathlib.Path:
    return CURRENT_DIR / "inputs" / "test_file.sdds.gz"


@pytest.fixture()
def _sdds_gzipped_file_str() -> str:
    return os.path.join(os.path.dirname(__file__), "inputs", "test_file.sdds.gz")


@pytest.fixture()
def _sdds_file_little_endian() -> pathlib.Path:
    return CURRENT_DIR / "inputs" / "test_file_little_endian.sdds"


@pytest.fixture()
def _sdds_file_lei1() -> pathlib.Path:
    return CURRENT_DIR / "inputs" / "LEI_1.sdds"


@pytest.fixture()
def _sdds_file_lei2() -> pathlib.Path:
    return CURRENT_DIR / "inputs" / "LEI_2.sdds"


@pytest.fixture()
def tmp_file(tmp_path) -> pathlib.Path:
    return tmp_path / "random_file"
