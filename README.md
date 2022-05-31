# SDDS
[![Cron Testing](https://github.com/pylhc/sdds/workflows/Cron%20Testing/badge.svg)](https://github.com/pylhc/sdds/actions?query=workflow%3A%22Cron+Testing%22)
[![Code Climate coverage](https://img.shields.io/codeclimate/coverage/pylhc/sdds.svg?style=popout)](https://codeclimate.com/github/pylhc/sdds)
[![Code Climate maintainability (percentage)](https://img.shields.io/codeclimate/maintainability-percentage/pylhc/sdds.svg?style=popout)](https://codeclimate.com/github/pylhc/sdds)
<!-- [![GitHub last commit](https://img.shields.io/github/last-commit/pylhc/sdds.svg?style=popout)](https://github.com/pylhc/sdds/) -->
[![PyPI Version](https://img.shields.io/pypi/v/sdds?label=PyPI&logo=pypi)](https://pypi.org/project/sdds/)
[![GitHub release](https://img.shields.io/github/v/release/pylhc/sdds?logo=github)](https://github.com/pylhc/sdds/)
[![Conda-forge Version](https://img.shields.io/conda/vn/conda-forge/sdds?color=orange&logo=anaconda)](https://anaconda.org/conda-forge/sdds)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.5705820.svg)](https://doi.org/10.5281/zenodo.5705820)

This package provides reading and writing functionality for [**self describing data sets (sdds)**](https://ops.aps.anl.gov/SDDSIntroTalk/slides.html) files.
On the python side, the data is stored in a class structure with attributes corresponding to the sdds-format itself (see [sdds-format](https://ops.aps.anl.gov/manuals/SDDStoolkit/SDDStoolkitsu2.html)). 

See the [API documentation](https://pylhc.github.io/sdds/) for details.

## Installing

Installation is easily done via `pip`:
```bash
python -m pip install sdds
```

One can also install in a `conda` environment via the `conda-forge` channel with:
```bash
conda install -c conda-forge sdds
```

## Example Usage

```python
import sdds

sdds_data = sdds.read("path_to_input.sdds")
sdds.write(sdds_data, "path_to_output.sdds")
```

### Read files with different endianness

By default the endianness (byte order) of the file is determined either by
a comment `!# little-endian` or `!# big-endian` in the header of the file.
If this comment is not found, the endianness of the running machine is assumed.

One can force a certain kind of endianness to the reader by supplying it to 
the read function:

```python
import sdds

sdds_data = sdds.read("path_to_input_with_big_endian.sdds", endianness="big")
sdds_data = sdds.read("path_to_input_with_little_endian.sdds", endianness="little")
```

Be aware that `sdds.write` will always write the file in big-endian order and 
will also leave a comment in the file, so that the reader can determine the
endianness and there is no need to supply it when reading 
a file written by this package.

## Known Issues

- Can't read binary columns
- No support for `&include` tag

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
