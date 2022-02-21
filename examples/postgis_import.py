#!/usr/bin/env python

'''
gsconfig is a python library for manipulating a GeoServer instance via the GeoServer RESTConfig API.

The project is distributed under a MIT License .
'''

__author__ = "David Winslow"
__copyright__ = "Copyright 2012-2018 Boundless, Copyright 2010-2012 OpenPlans"
__license__ = "MIT"

from geoserver.catalog import Catalog

cat = Catalog("http://localhost:8080/geoserver/rest", "admin", "geoserver")

ds = cat.create_datastore(name)
ds.connection_parameters.update(
    host="localhost",
    port="5432",
    database="gis",
    user="postgres",
    passwd="",
    dbtype="postgis")

cat.save(ds)
ds = cat.get_store(name)
components = dict((ext, f"myfile.{ext}") for ext in ["shp", "prj", "shx", "dbf"])
cat.add_data_to_store(ds, "mylayer", components)
