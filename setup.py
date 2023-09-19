"""Installs the RAFI application as a package.
"""

from setuptools import find_packages, setup

setup(
    name="pipeline",
    version="0.1.0",
    packages=find_packages(
        include=[
            "pipeline"
        ]
    ),
    install_requires=[],
)
