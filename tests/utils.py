# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010-2011 OpenStack, LLC
# Copyright 2012 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Common utilities used in testing"""

import __builtin__
import imp
import stubout
import subprocess
import sys
import unittest

from openstack.common import cfg

CONF = cfg.CONF


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.stubs = stubout.StubOutForTesting()

    def tearDown(self):
        super(BaseTestCase, self).tearDown()
        CONF.reset()
        self.stubs.UnsetAll()
        self.stubs.SmartUnsetAll()

    def config(self, **kw):
        """
        Override some configuration values.

        The keyword arguments are the names of configuration options to
        override and their values.

        If a group argument is supplied, the overrides are applied to
        the specified configuration option group.

        All overrides are automatically cleared at the end of the current
        test by the tearDown() method.
        """
        group = kw.pop('group', None)
        for k, v in kw.iteritems():
            CONF.set_override(k, v, group)


class FakeImporter(object):

    """Helper to mock module imports.

    Example usage:

    >>> fi = FakeImporter()
    >>> fi.fake_module('blaamod', 'print "blaamod"')
    >>> fi.setup()
    >>> import blaamod
    blaamod
    >>> fi.teardown()
    >>> import blaamod
    Traceback (most recent call last):
        ...
    ImportError: No module named blaamod
    """
    def __init__(self):
        self._orig_import = __import__
        self._faked_modules = {}

    def fake_module(self, fake_name, fake_code):
        self._faked_modules[fake_name] = fake_code

    def _import_wrapper(self, mod_name, *args, **kwargs):
        if mod_name not in self._faked_modules:
            self._orig_import(mod_name, *args, **kwargs)
            return

        if mod_name in sys.modules:
            return

        mod = imp.new_module(mod_name)
        exec self._faked_modules[mod_name] in mod.__dict__
        sys.modules[mod_name] = mod

    def setup(self):
        __builtin__.__import__ = self._import_wrapper

    def teardown(self):
        __builtin__.__import__ = self._orig_import

        for mod_name in self._faked_modules:
            try:
                del sys.modules[mod_name]
            except KeyError:
                pass
