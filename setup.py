#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

try:
    readme_text = open("README.rst", "r").read()
except IOError:
    readme_text = ""

setup(
    name="geoserver-restconfig",
    version="2.0.14",
    description="GeoServer REST Configuration",
    long_description=readme_text,
    keywords="GeoServer REST Configuration",
    license="MIT",
    url="https://github.com/GeoNode/geoserver-restconfig",
    author="David Winslow, Sebastian Benthall, Alessio Fabiani",
    author_email="alessio.fabiani@gmail.com",
    install_requires=[
        "requests >= 2.14.0",
        "gisdata >= 0.5.4",
        "six >= 1.12.0",
        "future",
    ],
    package_dir={"": "src"},
    packages=find_packages("src"),
    # test_suite="test.servicestests",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Scientific/Engineering :: GIS",
        "Programming Language :: Python :: 3.8",
    ],
)
