"""Installs the RAFI application as a package.
"""

from setuptools import find_packages, setup

setup(
    name="rafi",
    version="0.1.0",
    packages=find_packages(where="pipeline"),
    package_dir={"": "pipeline"},
    install_requires=[],
)
