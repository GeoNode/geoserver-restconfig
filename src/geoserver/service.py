# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright 2019, GeoSolutions Sas.
# Jendrusk also was here
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
    write_dict,
    write_string,
    write_int,
    string_list,
    key_value_pairs,
    write_string_list)


def service_from_index(catalog, node):
    if node.tag == "wms":
        bclass = ServiceWmsSettings
    elif node.tag == "wfs":
        bclass = ServiceWfsSettings
    elif node.tag == "wcs":
        bclass = ServiceWcsSettings
    elif node.tag == "wmts":
        bclass = ServiceWmtsSettings
    else:
        return None

    res = bclass(
        catalog=catalog,
        workspace=node.find("workspace").find("name").text if node.find("workspace") is not None else None
    )

    return res


class Watermark(object):
    def __init__(self, _enabled, _position, _transparency):
        self.enabled = _enabled
        self.position = _position
        self.transparency = _transparency


def watermark(node):
    enabled = node.find("enabled").text if node.find("enabled") is not None else None
    position = node.find("position").text if node.find("position") is not None else None
    transparency = node.find("transparency").text if node.find("transparency") is not None else None
    return Watermark(enabled, position, transparency)


def write_watermark_xml(watermark):
    def write(builder, watermark):
        builder.start("watermark", dict())
        # enabled
        builder.start("enabled", dict())
        builder.data(watermark.enabled)
        builder.end("enabled")
        # position
        builder.start("position", dict())
        builder.data(watermark.position)
        builder.end("position")
        # transparency
        builder.start("transparency", dict())
        builder.data(watermark.transparency)
        builder.end("transparency")
        builder.end("watermark")

    return write


def util_version(node):
    res = [x.text for x in node.iter("version")]
    return res


def write_util_version(versions):
    def write(builder, versions):
        builder.start("versions", dict())
        for ver in versions:
            builder.start("org.geotools.util.Version", dict())
            builder.start("version", dict())
            builder.data(ver)
            builder.end("version")
            builder.end("org.geotools.util.Version")
        builder.end("versions")

    return write


class Gml(object):
    def __init__(self, _srsNameStyle, _overrideGMLAttributes):
        self.srsNameStyle = _srsNameStyle
        self.overrideGMLAttributes = _overrideGMLAttributes


class GmlEntry(object):
    def __init__(self, _version, _gml):
        self.version = _version
        self.gml = _gml


def gml(node):
    gmls = []
    for ent in node.iter("entry"):
        version = ent.find("version").text if ent.find("version") is not None else None
        el_gml = ent.find("gml")
        srs = el_gml.find("srsNameStyle").text if el_gml.find("srsNameStyle") is not None else None
        override = el_gml.find("overrideGMLAttributes").text if el_gml.find(
            "overrideGMLAttributes") is not None else None
        res_gml = Gml(_srsNameStyle=srs, _overrideGMLAttributes=override)
        res = GmlEntry(_version=version, _gml=res_gml)
        gmls.append(res)
    return gmls


def write_gml(gml_list):
    def write(builder, gml_list):
        builder.start("gml", dict())
        for gmlen in gml_list:
            builder.start("entry", dict())
            builder.start("version", dict())
            builder.data(gmlen.version)
            builder.end("version")
            builder.start("gml", dict())
            builder.start("srsNameStyle", dict())
            builder.data(gmlen.gml.srsNameStyle)
            builder.end("srsNameStyle")
            builder.start("overrideGMLAttributes", dict())
            builder.data(gmlen.gml.overrideGMLAttributes)
            builder.end("overrideGMLAttributes")
            builder.end("gml")
            builder.end("entry")

        builder.end("gml")

    return write


class ServiceCommon(ResourceInfo):
    resource_type = ""
    save_method = "put"

    def __init__(self, catalog, workspace):
        super(ServiceCommon, self).__init__()
        self._catalog = catalog
        self._workspace_name = workspace
        self._workspace = None

    @property
    def catalog(self):
        return self._catalog

    @property
    def workspace(self):
        if self._workspace is None and self._workspace_name is not None:
            self._workspace = self.catalog.get_workspace(self._workspace_name)
            return self._workspace
        else:
            return None

    @property
    def href(self):
        if self._workspace_name is not None:
            return urljoin(
                f"{self.catalog.service_url}/",
                f"services/{self.resource_type}/workspaces/{self._workspace_name}/settings"
            )
        else:
            return f"{self.catalog.service_url}/services/{self.resource_type}/settings"

    enabled = xml_property("enabled", lambda x: x.text == 'true')
    name = xml_property("name")
    title = xml_property("title")
    maintainer = xml_property("maintainer")
    abstrct = xml_property("abstrct")
    accessConstraints = xml_property("accessConstraints")
    fees = xml_property("fees")
    versions = xml_property("versions", util_version)
    keywords = xml_property("keywords", string_list)
    citeCompliant = xml_property("citeCompliant", lambda x: x.text == 'true')
    onlineResource = xml_property("onlineResource")
    schemaBaseURL = xml_property("schemaBaseURL")
    verbose = xml_property("verbose", lambda x: x.text == 'true')

    writers = {
        'enabled': write_bool("enabled"),
        "name": write_string("name"),
        "title": write_string("title"),
        "versions": write_util_version("versions"),
        "maintainer": write_string("maintainer"),
        "abstrct": write_string("abstrct"),
        "accessConstraints": write_string("accessConstraints"),
        "fees": write_string("fees"),
        "keywords": write_string_list("keywords"),
        "citeCompliant": write_bool("citeCompliant"),
        "onlineResource": write_string("onlineResource"),
        "schemaBaseURL": write_string("schemaBaseURL"),
        "verbose": write_bool("verbose")
    }


class ServiceWmsSettings(ServiceCommon):
    resource_type = "wms"

    metadata = xml_property("metadata", key_value_pairs)
    watermark = xml_property("watermark", watermark)
    interpolation = xml_property("interpolation")
    getFeatureInfoMimeTypeCheckingEnabled = xml_property("getFeatureInfoMimeTypeCheckingEnabled",
                                                         lambda x: x.text == 'true')
    dynamicStylingDisabled = xml_property("dynamicStylingDisabled", lambda x: x.text == 'true')
    maxBuffer = xml_property("maxBuffer", lambda x: int(x.text))
    maxRequestMemory = xml_property("maxRequestMemory", lambda x: int(x.text))
    maxRenderingTime = xml_property("maxRenderingTime", lambda x: int(x.text))
    maxRenderingErrors = xml_property("maxRenderingErrors", lambda x: int(x.text))

    writers = dict(ServiceCommon.writers)
    writers.update({
        "metadata": write_dict("metadata"),
        "watermark": write_watermark_xml("watermark"),
        "interpolation": write_string("interpolation"),
        "getFeatureInfoMimeTypeCheckingEnabled": write_bool("getFeatureInfoMimeTypeCheckingEnabled"),
        "dynamicStylingDisabled": write_bool("dynamicStylingDisabled"),
        "maxBuffer": write_int("maxBuffer"),
        "maxRequestMemory": write_int("maxRequestMemory"),
        "maxRenderingTime": write_int("maxRenderingTime"),
        "maxRenderingErrors": write_int("maxRenderingErrors")
    })


class ServiceWfsSettings(ServiceCommon):
    resource_type = "wfs"

    metadataLink = xml_property("metadataLink", key_value_pairs)
    gml = xml_property("gml", gml)
    serviceLevel = xml_property("serviceLevel")
    maxFeatures = xml_property("maxFeatures", lambda x: int(x.text))
    featureBounding = xml_property("featureBounding", lambda x: x.text == 'true')
    canonicalSchemaLocation = xml_property("canonicalSchemaLocation", lambda x: x.text == 'true')
    encodeFeatureMember = xml_property("encodeFeatureMember", lambda x: x.text == 'true')
    hitsIgnoreMaxFeatures = xml_property("hitsIgnoreMaxFeatures", lambda x: x.text == 'true')

    writers = dict(ServiceCommon.writers)
    writers.update({
        "gml": write_gml("gml"),
        "serviceLevel": write_string("serviceLevel"),
        "maxFeatures": write_int("maxFeatures"),
        "featureBounding": write_bool("featureBounding"),
        "canonicalSchemaLocation": write_bool("canonicalSchemaLocation"),
        "encodeFeatureMember": write_bool("encodeFeatureMember"),
        "hitsIgnoreMaxFeatures": write_bool("hitsIgnoreMaxFeatures"),
    })


class ServiceWcsSettings(ServiceCommon):
    resource_type = "wcs"

    metadataLink = xml_property("metadataLink", key_value_pairs)
    gmlPrefixing = xml_property("gmlPrefixing", lambda x: x.text == 'true')
    latLon = xml_property("latLon", lambda x: x.text == 'true')
    maxInputMemory = xml_property("maxInputMemory", lambda x: int(x.text))
    maxOutputMemory = xml_property("maxOutputMemory", lambda x: int(x.text))

    writers = dict(ServiceCommon.writers)
    writers.update({
        "metadataLink": write_dict("metadataLink"),
        "gmlPrefixing": write_bool("gmlPrefixing"),
        "latLon": write_bool("latLon"),
        "maxInputMemory": write_int("maxInputMemory"),
        "maxOutputMemory": write_int("maxOutputMemory")
    })


class ServiceWmtsSettings(ServiceCommon):
    resource_type = "wmts"
