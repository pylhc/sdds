# SDDS

This package provides reading and writing functionality for **self describing data sets (sdds)**. 

## Getting Started

### Prerequisites

The only third-party package sdds depends on is `numpy`.


### Installing

Installation is easily done via `pip`. The package is then used as `sdds`.

```
pip install sdds
```

Example:

```
import sdds

sdds_data = sdds.read('path_to_input.sdds')
sdds.write(sdds_data, 'path_to_output.sdds')
```


## Description

Reading and writing capabilities for [sdds-files](https://ops.aps.anl.gov/SDDSIntroTalk/slides.html)
are provided by this package. On the python side, the data is stored in a class structure
with attributes corresponding to the sdds-format itself 
(see [sdds-format](https://ops.aps.anl.gov/manuals/SDDStoolkit/SDDStoolkitsu2.html)).


## Known Issues

- Can't read ASCII files
- Can't read binary columns
- No support for `&include` tag


## Authors

* **Jaime** - *Initial work* - [jaimecp89](https://github.com/jaimecp89)
* **Lukáš** - *Other work* - [lmalina](https://github.com/lmalina)
* **Josch** - *Publishing* - [JoschD](https://github.com/JoschD)
* **pyLHC/OMC-Team** - *Working Group* - [pyLHC](https://github.com/orgs/pylhc/teams/omc-team)


## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

