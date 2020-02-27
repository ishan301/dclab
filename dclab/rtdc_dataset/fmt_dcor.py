#!/usr/bin/python
# -*- coding: utf-8 -*-
"""DCOR client interface"""
from __future__ import division, print_function, unicode_literals

import numpy as np
import requests

from .. import definitions as dfn
from ..util import hashobj

from .config import Configuration
from .core import RTDCBase


class APIHandler(object):
    """Handles the DCOR api with caching for simple queries"""
    cache_queries = ["metadata", "size", "feature_list"]

    def __init__(self, url, api_headers):
        self.url = url
        self.api_headers = api_headers
        self._cache = {}

    def get(self, query, feat=None, trace=None, event=None):
        if query in APIHandler.cache_queries and query in self._cache:
            result = self._cache[query]
        else:
            qstr = "&query={}".format(query)
            if feat is not None:
                qstr += "&feature={}".format(feat)
            if trace is not None:
                qstr += "&trace={}".format(trace)
            if event is not None:
                qstr += "&event={}".format(event)
            apicall = self.url + qstr
            req = requests.get(apicall, headers=self.api_headers)
            if not req.ok:
                raise ConnectionError("Error accessing {}: {}".format(
                    apicall, req.reason))
            result = req.json()["result"]
            if query in APIHandler.cache_queries:
                self._cache[query] = result
        return result


class EventFeature(object):
    """Helper class for accessing non-scalar features event-wise"""

    def __init__(self, feature, api):
        self.identifier = api.url + ":" + feature  # for caching ancillaries
        self.feature = feature
        self.api = api

    def __iter__(self):
        for idx in range(len(self)):
            yield self[idx]

    def __getitem__(self, event):
        data = self.api.get(query="feature", feat=self.feature, event=event)
        return np.asarray(data)

    def __len__(self):
        return int(self.api.get(query="size"))


class EventTrace(object):
    """Helper class for accessing traces event-wise"""

    def __init__(self, trace, api):
        self.identifier = api.url + ":" + trace  # for caching ancillaries
        self.trace = trace
        self.api = api

    def __iter__(self):
        for idx in range(len(self)):
            yield self[idx]

    def __getitem__(self, event):
        data = self.api.get(query="trace", trace=self.trace, event=event)
        return np.asarray(data)

    def __len__(self):
        return int(self.api.get(query="size"))


class EventTraceFeature(object):
    """Helper class for accessing traces"""

    def __init__(self, api):
        self.identifier = api.url + ":traces"
        self.api = api
        self.traces = api.get(query="trace_list")

    def __contains__(self, key):
        return key in self.traces

    def __getitem__(self, trace):
        if trace in self.traces:
            return EventTrace(trace, self.api)

    def keys(self):
        return self.traces


class FeatureCache(object):
    """Download and cache (scalar only) features from DCOR"""

    def __init__(self, api):
        self.api = api
        self._features = self.api.get(query="feature_list")
        self._scalar_cache = {}

    def __contains__(self, key):
        return key in self._features

    def __getitem__(self, key):
        # user-level checking is done in core.py
        assert key in dfn.feature_names
        if key not in self._features:
            raise KeyError("Feature '{}' not found!".format(key))

        if key in self._scalar_cache:
            return self._scalar_cache[key]
        elif key in dfn.scalar_feature_names:
            # download the feature and cache it
            feat = np.asarray(self.api.get(query="feature", feat=key))
            self._scalar_cache[key] = feat
            return feat
        elif key == "trace":
            return EventTraceFeature(self.api)
        else:
            return EventFeature(key, self.api)

    def __iter__(self):
        # dict-like behavior
        for key in self.keys():
            yield key

    def keys(self):
        return self._features


class RTDC_DCOR(RTDCBase):
    def __init__(self, url, use_ssl=True, host="dcor.mpl.mpg.de",
                 api_key="", *args, **kwargs):
        """Wrap around the DCOR API

        Parameters
        ----------
        url: str
            Full URL or resource identifier; valid values are

            - https://dcor.mpl.mpg.de/api/3/action/dcserv?id=caab96f6-
              df12-4299-aa2e-089e390aafd5'
            - dcor.mpl.mpg.de/api/3/action/dcserv?id=caab96f6-df12-
              4299-aa2e-089e390aafd5
            - caab96f6-df12-4299-aa2e-089e390aafd5
        use_ssl: bool
            Set this to False to disable SSL (should only be used for
            testing)
        host: str
            The host machine (required if the host is not given
            in the URL)
        api_key: str
            API key to access private resources
        *args:
            Arguments for `RTDCBase`
        **kwargs:
            Keyword arguments for `RTDCBase`

        Attributes
        ----------
        path: str
            Full URL to the DCOR resource
        """
        super(RTDC_DCOR, self).__init__(*args, **kwargs)

        self._hash = None
        self.path = RTDC_DCOR.get_full_url(url, use_ssl, host)
        self.api = APIHandler(url=self.path,
                              api_headers={"Authorization": api_key})

        # Parse configuration
        self.config = Configuration(cfg=self.api.get(query="metadata"))

        # Get size
        self._size = int(self.api.get(query="size"))

        # Setup events
        self._events = FeatureCache(self.api)

        # Override logs property with HDF5 data
        self.logs = {}

        self.title = "{} - M{}".format(self.config["experiment"]["sample"],
                                       self.config["experiment"]["run index"])

        # Set up filtering
        self._init_filters()

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        pass

    def __len__(self):
        return self._size

    @staticmethod
    def get_full_url(url, use_ssl, host):
        """Return the full URL to a DCOR resource"""
        if use_ssl:
            web = "https"
        else:
            web = "http"
        if url.count("://"):
            base = url.split("://", 1)[1]
        else:
            base = url
        if base.count("/"):
            host, api = base.split("/", 1)
        else:
            api = "api/3/action/dcserv?id=" + base
        new_url = "{}://{}/{}".format(web, host, api)
        return new_url

    @property
    def hash(self):
        """Hash value based on file name and content"""
        if self._hash is None:
            tohash = [self.path]
            self._hash = hashobj(tohash)
        return self._hash
