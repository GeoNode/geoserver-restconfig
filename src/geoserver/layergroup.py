# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright 2019, GeoSolutions Sas.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE.txt file in the root directory of this source tree.
#
#########################################################################

from six import string_types
try:
    from urllib.parse import urljoin
except BaseException:
    from urlparse import urljoin

from geoserver.support import ResourceInfo, bbox, write_bbox, write_string, xml_property, build_url

try:
    from past.builtins import basestring
except ImportError:
    pass


def _maybe_text(n):
    if n is None:
        return None
    else:
        return n.text


def _layer_list(node, element):
    if node is not None:
        return [_maybe_text(n.find("name")) for n in node.findall(element)]


def _style_list(node):
    if node is not None:
        return [_maybe_text(n.find("name")) for n in node.findall("style")]


def _write_layers(builder, layers, parent, element, attributes):
    builder.start(parent, dict())
    for l in layers:
        builder.start(element, attributes or dict())
        if l is not None:
            builder.start("name", dict())
            builder.data(l)
            builder.end("name")
        builder.end(element)
    builder.end(parent)


def _write_styles(builder, styles):
    builder.start("styles", dict())
    for s in styles:
        builder.start("style", dict())
        if s is not None:
            builder.start("name", dict())
            builder.data(s)
            builder.end("name")
        builder.end("style")
    builder.end("styles")


class LayerGroup(ResourceInfo):
    """
    Represents a layer group in geoserver
    """

    resource_type = "layerGroup"
    save_method = "PUT"

    def __init__(self, catalog, name, workspace=None):
        super(LayerGroup, self).__init__()

        assert isinstance(name, string_types)

        self.catalog = catalog
        self.name = name
        self.workspace = workspace

        # the XML format changed in 2.3.x - the element listing all the layers
        # and the entries themselves have changed
        if self.catalog.get_version() == "2.2.x":
            parent, element, attributes = "layers", "layer", None
        else:
            parent = "publishables"
            element = "published"
            attributes = {'type': 'layer'}
        self._layer_parent = parent
        self._layer_element = element
        self._layer_attributes = attributes
        self.writers = {
            'name': write_string("name"),
            'styles': _write_styles,
            'layers': lambda b, l: _write_layers(b, l, parent,
                                                 element, attributes),
            'bounds': write_bbox("bounds"),
            'workspace': write_string("workspace"),
            'mode': write_string("mode"),
            'abstractTxt': write_string("abstractTxt"),
            'title': write_string("title")
        }

    @property
    def href(self):
        path_parts = f"layergroups/{self.name}.xml"
        if self.workspace is not None and self.workspace:
            workspace_name = getattr(self.workspace, 'name', self.workspace)
            path_parts = f"workspaces/{workspace_name}/{path_parts}"
        return urljoin(
            f"{self.catalog.service_url}/",
            path_parts
        )

    styles = xml_property("styles", _style_list)
    bounds = xml_property("bounds", bbox)
    mode = xml_property("mode")
    abstract = xml_property("abstractTxt")
    title = xml_property("title")

    def _layers_getter(self):
        if "layers" in self.dirty:
            return self.dirty["layers"]
        else:
            if self.dom is None:
                self.fetch()
            node = self.dom.find(self._layer_parent)
            if node is not None:
                return _layer_list(node, self._layer_element)
            return None

    def _layers_setter(self, value):
        self.dirty["layers"] = value

    def _layers_delete(self):
        self.dirty["layers"] = None

    layers = property(_layers_getter, _layers_setter, _layers_delete)

    def __str__(self):
        return f"<LayerGroup {self.name}>"

    __repr__ = __str__


class UnsavedLayerGroup(LayerGroup):
    save_method = "POST"

    def __init__(self, catalog, name, layers, styles, bounds, mode, abstract, title, workspace = None):
        super(UnsavedLayerGroup, self).__init__(catalog, name, workspace=workspace)
        bounds = bounds if bounds is not None else ("-180", "180", "-90", "90", "EPSG:4326")
        self.dirty.update(
            name = name,
            layers = layers,
            styles = styles,
            bounds = bounds,
            workspace = workspace,
            mode = mode.upper(),
            abstractTxt = abstract,
            title = title
        )

    @property
    def href(self):
        query = {'name': self.name}
        path_parts = ['layergroups']
        if self.workspace is not None and self.workspace:
            workspace_name = getattr(self.workspace, 'name', self.workspace)
            path_parts = ["workspaces", workspace_name] + path_parts
        return build_url(self.catalog.service_url, path_parts, query)
