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
try:
    from urllib.parse import urljoin
except BaseException:
    from urlparse import urljoin

from geoserver.support import (
    ResourceInfo,
    xml_property,
    write_bool,
    workspace_from_url,
    resource_from_url,
)
from geoserver.style import Style


class _attribution(object):
    def __init__(self, title, width, height, href, url, type):
        self.title = title
        self.width = width
        self.height = height
        self.href = href
        self.url = url
        self.type = type


def _read_attribution(node):
    title = node.find("title")
    width = node.find("logoWidth")
    height = node.find("logoHeight")
    href = node.find("href")
    url = node.find("logoURL")
    type = node.find("logoType")

    if title is not None and title:
        title = title.text
    if width is not None and width:
        width = width.text
    if height is not None and height:
        height = height.text
    if href is not None and href:
        href = href.text
    if url is not None and url:
        url = url.text
    if type is not None and type:
        type = type.text

    return _attribution(title, width, height, href, url, type)


def _write_attribution(builder, attr):
    builder.start("attribution", dict())
    if attr.title is not None and attr.title:
        builder.start("title", dict())
        builder.data(attr.title)
        builder.end("title")
    if attr.width is not None and attr.width:
        builder.start("logoWidth", dict())
        builder.data(attr.width)
        builder.end("logoWidth")
    if attr.height is not None and attr.height:
        builder.start("logoHeight", dict())
        builder.data(attr.height)
        builder.end("logoHeight")
    if attr.href is not None and attr.href:
        builder.start("href", dict())
        builder.data(attr.href)
        builder.end("href")
    if attr.url is not None and attr.url:
        builder.start("logoURL", dict())
        builder.data(attr.url)
        builder.end("logoURL")
    if attr.type is not None and attr.type:
        builder.start("logoType", dict())
        builder.data(attr.type)
        builder.end("logoType")
    builder.end("attribution")


def _write_style_element(builder, name):
    ws, name = name.split(":") if ":" in name else (None, name)
    builder.start("name", dict())
    builder.data(name)
    builder.end("name")
    if ws:
        builder.start("workspace", dict())
        builder.data(ws)
        builder.end("workspace")


def _write_default_style(builder, name):
    builder.start("defaultStyle", dict())
    if name is not None and name:
        _write_style_element(builder, name)
    builder.end("defaultStyle")


def _write_alternate_styles(builder, styles):
    builder.start("styles", dict())
    for s in styles:
        builder.start("style", dict())
        _write_style_element(builder, getattr(s, "fqn", s))
        builder.end("style")
    builder.end("styles")


class Layer(ResourceInfo):
    def __init__(self, catalog, name):
        super(Layer, self).__init__()
        self.catalog = catalog
        self.name = name
        self.gs_version = self.catalog.get_short_version()

    resource_type = "layer"
    save_method = "PUT"

    @property
    def href(self):
        return urljoin(f"{self.catalog.service_url}/", f"layers/{self.name}.xml")

    @property
    def resource(self):
        if self.dom is None:
            self.fetch()
        name = self.dom.find("resource/name").text
        atom_link = [n for n in self.dom.find("resource") if "href" in n.attrib]
        ws_name = workspace_from_url(atom_link[0].get("href"))
        if self.gs_version >= "2.13":
            if ":" in name:
                ws_name, name = name.split(":", 1)
        store_name = resource_from_url(atom_link[0].get("href"), ws_name)
        _resources = self.catalog.get_resources(
            names=[name], stores=[store_name], workspaces=[ws_name]
        )
        return _resources[0] if len(_resources) > 0 else _resources

    def _get_default_style(self, recursive=False):
        if "default_style" in self.dirty:
            return self.dirty["default_style"]
        if self.dom is None:
            self.fetch()
        element = self.dom.find("defaultStyle")
        # aborted data uploads can result in no default style
        return self._resolve_style(element, recursive) if element is not None else None

    def _resolve_style(self, element, recursive=False):
        if (
            element
            and element.find("name") is not None
            and len(element.find("name").text)
        ):
            if ":" in element.find("name").text:
                ws_name, style_name = element.find("name").text.split(":")
            else:
                style_name = element.find("name").text
                ws_name = None
            atom_link = [n for n in element if "href" in n.attrib]
            if atom_link and ws_name is None:
                ws_name = workspace_from_url(atom_link[0].get("href"))
            return self.catalog.get_style(
                name=style_name, workspace=ws_name, recursive=recursive
            )
        return None

    def _set_default_style(self, style):
        if isinstance(style, Style):
            style = style.fqn
        self.dirty["default_style"] = style

    def _get_alternate_styles(self, recursive=False):
        if "alternate_styles" in self.dirty:
            return self.dirty["alternate_styles"]
        if self.dom is None:
            self.fetch()
        styles_list = self.dom.findall("styles/style")
        return [self._resolve_style(s, recursive) for s in styles_list]

    def _set_alternate_styles(self, styles):
        self.dirty["alternate_styles"] = styles

    default_style = property(_get_default_style, _set_default_style)
    styles = property(_get_alternate_styles, _set_alternate_styles)

    attribution_object = xml_property("attribution", _read_attribution)
    enabled = xml_property("enabled", lambda x: x.text == "true")
    advertised = xml_property("advertised", lambda x: x.text == "true", default=True)
    type = xml_property("type")

    # obtains uncached default style with original format (recursive retrieval)
    def get_full_default_style(self):
        return self._get_default_style(True)

    # obtains uncached alternate styles with original format (recursive retrieval)
    def get_full_styles(self):
        return self._get_alternate_styles(True)

    def _get_attr_attribution(self):
        obj = {
            "title": self.attribution_object.title,
            "width": self.attribution_object.width,
            "height": self.attribution_object.height,
            "href": self.attribution_object.href,
            "url": self.attribution_object.url,
            "type": self.attribution_object.type,
        }
        return obj

    def _set_attr_attribution(self, attribution):
        self.dirty["attribution"] = _attribution(
            attribution["title"],
            attribution["width"],
            attribution["height"],
            attribution["href"],
            attribution["url"],
            attribution["type"],
        )

        assert self.attribution_object.title == attribution["title"]
        assert self.attribution_object.width == attribution["width"]
        assert self.attribution_object.height == attribution["height"]
        assert self.attribution_object.href == attribution["href"]
        assert self.attribution_object.url == attribution["url"]
        assert self.attribution_object.type == attribution["type"]

    attribution = property(_get_attr_attribution, _set_attr_attribution)

    writers = {
        "attribution": _write_attribution,
        "enabled": write_bool("enabled"),
        "advertised": write_bool("advertised"),
        "default_style": _write_default_style,
        "alternate_styles": _write_alternate_styles,
    }
