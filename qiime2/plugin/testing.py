# ----------------------------------------------------------------------------
# Copyright (c) 2016-2018, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

import pkg_resources
import tempfile
import unittest
import shutil
import pathlib

import qiime2

from qiime2.plugin.model.base import FormatBase


# TODO Split out into more specific subclasses if necessary.
class TestPluginBase(unittest.TestCase):
    package = None
    test_dir_prefix = 'qiime2-plugin'

    def setUp(self):
        try:
            package = self.package.split('.')[0]
        except AttributeError:
            self.fail('Test class must have a package property.')

        # plugins are keyed by their names, so a search inside the plugin
        # object is required to match to the correct plugin
        plugin = None
        for name, plugin_ in qiime2.sdk.PluginManager().plugins.items():
            if plugin_.package == package:
                plugin = plugin_

        if plugin is not None:
            self.plugin = plugin
        else:
            self.fail('%s is not a registered QIIME 2 plugin.' % package)

        # TODO use qiime2 temp dir when ported to framework, and when the
        # configurable temp dir exists
        self.temp_dir = tempfile.TemporaryDirectory(
            prefix='%s-test-temp-' % self.test_dir_prefix)

    def tearDown(self):
        self.temp_dir.cleanup()

    def get_data_path(self, filename):
        return pkg_resources.resource_filename(self.package,
                                               'data/%s' % filename)

    def get_transformer(self, from_type, to_type):
        try:
            transformer_record = self.plugin.transformers[from_type, to_type]
        except KeyError:
            self.fail(
                "Could not find registered transformer from %r to %r." %
                (from_type, to_type))

        return transformer_record.transformer

    def assertRegisteredSemanticType(self, semantic_type):
        try:
            semantic_type_record = self.plugin.types[semantic_type.name]
        except KeyError:
            self.fail(
                "Semantic type %r is not registered on the plugin." %
                semantic_type)

        obs_semantic_type = semantic_type_record.semantic_type

        self.assertEqual(obs_semantic_type, semantic_type)

    def assertSemanticTypeRegisteredToFormat(self, semantic_type, exp_format):
        obs_format = None
        for type_format_record in self.plugin.type_formats:
            if type_format_record.type_expression == semantic_type:
                obs_format = type_format_record.format
                break

        self.assertIsNotNone(
            obs_format,
            "Semantic type %r is not registered to a format." % semantic_type)

        self.assertEqual(
            obs_format, exp_format,
            "Expected semantic type %r to be registered to format %r, not %r."
            % (semantic_type, exp_format, obs_format))

    def transform_format(self, source_format, target, filename=None,
                         filenames=None):
        # Guard any non-QIIME2 Format sources from being tested
        if not issubclass(source_format, FormatBase):
            raise ValueError("`source_format` must be a subclass of "
                             "FormatBase.")

        # Guard against invalid filename(s) usage
        if filename is not None and filenames is not None:
            raise ValueError("Cannot use both `filename` and `filenames` at "
                             "the same time.")

        # Handle format initialization
        source_path = None
        if filename:
            source_path = self.get_data_path(filename)
        elif filenames:
            source_path = self.temp_dir.name
            for filename in filenames:
                filepath = self.get_data_path(filename)
                shutil.copy(filepath, source_path)
        input = source_format(source_path, mode='r')

        transformer = self.get_transformer(source_format, target)
        obs = transformer(input)

        if issubclass(target, FormatBase):
            self.assertIsInstance(obs, (type(pathlib.Path()), str, target))
        else:
            self.assertIsInstance(obs, target)

        return input, obs
