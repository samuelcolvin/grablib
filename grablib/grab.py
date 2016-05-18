from __future__ import unicode_literals

import json
import collections

import yaml
from yaml.scanner import MarkedYAMLError

from .common import GrablibError, logger, DEFAULT_OPTIONS
from . import download, minify


def grab(config_file, **options):
    """
    Process a file or json string defining files to download and what to do with them.

    :param config_file: relative path to file defining what to download
    :param options: additional options, these override anything in file_path, eg. from terminal
    :return: boolean, whether or not files have been downloaded
    """
    if config_file.strip().startswith('{'):
        # special case we assume raw json, note: this doesn't give a nicely formatted error if json is invalid
        config_data = json.loads(config_file, object_pairs_hook=collections.OrderedDict)
    else:
        loader = yaml_or_json(str(config_file))
        with open(config_file) as f:
            try:
                config_data = loader(f)
            except (MarkedYAMLError, ValueError) as e:
                logger.error('%s: %s', e.__class__.__name__, e)
                raise GrablibError('error loading "{}"'.format(config_file))

    libs_info, minify_info, file_options = process_obj(config_data)

    kwarg_options = options.copy()
    options = DEFAULT_OPTIONS.copy()
    options.update({k: v for k, v in file_options.items() if v is not None})
    options.update({k: v for k, v in kwarg_options.items() if v is not None})
    if libs_info:
        download.DownloadLibs(libs_info, **options).download()
    if minify_info:
        minify.MinifyLibs(minify_info, **options).minify()


def process_obj(data):
    """
    Takes a json object and extracts libs_info and options
    """
    options = {}
    if 'libs' in data or 'minify' in data:
        libs_info = data.get('libs', None)
        minify_info = data.get('minify', None)

        for k, v in data.items():
            if k in DEFAULT_OPTIONS:
                options[k] = v
    else:
        libs_info, minify_info = None, None
        libs_info = data
    return libs_info, minify_info, options


def yaml_load(f):
    class OrderedLoader(yaml.Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return collections.OrderedDict(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(f, OrderedLoader)


def json_load(f):
    return json.load(f, object_pairs_hook=collections.OrderedDict)


def yaml_or_json(file_path):
    if any(file_path.endswith(ext) for ext in ['.yaml', '.yml']):
        logger.debug('Processing %s as a yaml file', file_path)
        return yaml_load
    elif file_path.endswith('.json'):
        logger.debug('Processing %s as a json file', file_path)
        return json_load
    else:
        raise GrablibError('Unexpected extension for "{}", should be json or yml/yaml'.format(file_path))
