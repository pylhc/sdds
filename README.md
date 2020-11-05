# SDDS
[![Cron Testing](https://github.com/pylhc/sdds/workflows/Cron%20Testing/badge.svg)](https://github.com/pylhc/sdds/actions?query=workflow%3A%22Cron+Testing%22)
[![Code Climate coverage](https://img.shields.io/codeclimate/coverage/pylhc/sdds.svg?style=popout)](https://codeclimate.com/github/pylhc/sdds)
[![Code Climate maintainability (percentage)](https://img.shields.io/codeclimate/maintainability-percentage/pylhc/sdds.svg?style=popout)](https://codeclimate.com/github/pylhc/sdds)
[![GitHub last commit](https://img.shields.io/github/last-commit/pylhc/sdds.svg?style=popout)](https://github.com/pylhc/sdds/)
[![GitHub release](https://img.shields.io/github/release/pylhc/sdds.svg?style=popout)](https://github.com/pylhc/sdds/)

## Description

This package provides reading and writing functionality for [**self describing data sets (sdds)**](https://ops.aps.anl.gov/SDDSIntroTalk/slides.html) files.
On the python side, the data is stored in a class structure with attributes corresponding to the sdds-format itself (see [sdds-format](https://ops.aps.anl.gov/manuals/SDDStoolkit/SDDStoolkitsu2.html)). 

## Getting Started

Installation is easily done via `pip`. The package is then used as `sdds`.

```
pip install sdds
```

Example use:

```python
import sdds

sdds_data = sdds.read("path_to_input.sdds")
sdds.write(sdds_data, "path_to_output.sdds")
```

## Known Issues

- Can't read binary columns
- No support for `&include` tag

## Authors

* **Jaime** - *Initial work* - [jaimecp89](https://github.com/jaimecp89)
* **Lukáš** - *Other work* - [lmalina](https://github.com/lmalina)
* **Josch** - *Publishing* - [JoschD](https://github.com/JoschD)
* **pyLHC/OMC-Team** - *Working Group* - [pyLHC](https://github.com/orgs/pylhc/teams/omc-team)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

