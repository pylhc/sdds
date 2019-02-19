import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="sdds",
    version="0.1.0",
    description="Read and write sdds files.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/pylhc/sdds",
    author="pyLHC",
    author_email="pylhc@github.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
    packages=["sdds"],
    install_requires=["numpy"],
)