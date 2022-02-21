'''
gsconfig is a python library for manipulating a GeoServer instance via the GeoServer RESTConfig API.

The project is distributed under a MIT License .
'''

__author__ = "David Winslow"
__copyright__ = "Copyright 2012-2018 Boundless, Copyright 2010-2012 OpenPlans"
__license__ = "MIT"

from geoserver.catalog import Catalog

demo = Catalog("http://localhost:8080/geoserver/rest",
               "admin", "geoserver")

live = Catalog("http://localhost:8080/geoserver2/rest",
               "admin", "geoserver")

groupname = "Wayne"
prefix = "wayne_"


def resolve(layer, style):
    if style is not None and style:
        return (layer, style)
    else:
        return (layer, demo.get_layer(layer).default_style.name)


g = demo.get_layergroup("groupname")
resolved = [resolve(l, s) for (l, s) in zip(g.layers, g.styles)]

# upload all styles to live
for (l, s) in resolved:
    wayne_style = prefix + s
    style_on_server = live.get_style(wayne_style)
    sld = demo.get_style(s).sld_body
    if style_on_server is None:
        live.create_style(wayne_style, sld)
    else:
        style_on_server.update_body(sld)

backup_layernames = {}

# check that all requisite layers exist!
for (l, s) in resolved:
    assert live.get_layer(l) is not None or l in backup_layernames, l

lyrs = [backup_layernames.get(x[0], x[0]) for x in resolved]
stls = [(prefix + x[1]) for x in resolved]
wayne_group = live.get_layergroup(groupname)
if wayne_group is None:
    wayne_group = live.create_layergroup(groupname)
wayne_group.layers = lyrs
wayne_group.styles = stls
live.save(wayne_group)
