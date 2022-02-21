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

pg_stores = [s.name for s in cat.get_stores()
             if s.resource_type == 'dataStore' and s.connection_parameters.get("dbtype") == "postgis"]

print(cat.get_resources(stores=pg_stores))
