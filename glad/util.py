import functools
import os
import re
import sys
from collections import namedtuple


if sys.version_info >= (3, 0, 0):
    basestring = str


Version = namedtuple('Version', ['major', 'minor'])


_API_NAMES = {
    'egl': 'EGL',
    'gl': 'OpenGL',
    'gles1': 'OpenGL ES',
    'gles2': 'OpenGL ES',
    'glsc2': 'OpenGL SC',
    'glx': 'GLX',
    'wgl': 'WGL',
}


def api_name(api):
    api = api.lower()
    return _API_NAMES.get(api, api.upper())


def makefiledir(path):
    dir = os.path.split(path)[0]
    if not os.path.exists(dir):
        os.makedirs(dir)


ApiInformation = namedtuple('ApiInformation', ('specification', 'version', 'profile'))
_API_SPEC_MAPPING = {
    'opencl': 'cl',
    'gl': 'gl',
    'gles1': 'gl',
    'gles2': 'gl',
    'glsc2': 'gl',
    'egl': 'egl',
    'glx': 'glx',
    'wgl': 'wgl',
    'vulkan': 'vk'
}


def parse_version(value):
    if value is None:
        return None

    value = value.strip()
    if not value:
        return None

    major, minor = (value + '.0').split('.')[:2]
    return Version(int(major), int(minor))


def parse_apis(value, api_spec_mapping=_API_SPEC_MAPPING):
    result = dict()

    for api in value.split(','):
        api = api.strip()

        m = re.match(
            r'^(?P<api>\w+)(:(?P<profile>\w+))?(/(?P<spec>\w+))?(=(?P<version>\d+(\.\d+)?)?)?$',
            api
        )

        if m is None:
            raise ValueError('Invalid API {}'.format(api))

        spec = m.group('spec')
        if spec is None:
            try:
                spec = api_spec_mapping[m.group('api')]
            except KeyError:
                raise ValueError('Can not resolve specification for API {}'.format(m.group('api')))

        version = parse_version(m.group('version'))

        result[m.group('api')] = ApiInformation(spec, version, m.group('profile'))

    return result


# based on https://stackoverflow.com/a/11564323/969534
def topological_sort(items, key, dependencies):
    pending = [(item, set(dependencies(item))) for item in items]
    emitted = []
    while pending:
        next_pending = []
        next_emitted = []
        for entry in pending:
            item, deps = entry
            deps.difference_update(emitted)
            if deps:
                next_pending.append(entry)
            else:
                yield item
                key_item = key(item)
                emitted.append(key_item)
                next_emitted.append(key_item)
        if not next_emitted:
            raise ValueError("cyclic or missing dependency detected: %r" % (next_pending,))
        pending = next_pending
        emitted = next_emitted


def memoize(key=None):
    def _default_key_func(*args, **kwargs):
        return tuple(args), tuple(kwargs.items())

    key_func = _default_key_func if key is None else key

    def memoize_decorator(func):
        cache = dict()

        @functools.wraps(func)
        def memoized(*args, **kwargs):
            key = key_func(*args, **kwargs)
            if key not in cache:
                cache[key] = func(*args, **kwargs)
            return cache[key]

        return memoized

    return memoize_decorator


def itertext(element, ignore=()):
    tag = element.tag
    if not isinstance(tag, basestring) and tag is not None:
        return
    if element.text:
        yield element.text
    for e in element:
        if not e.tag in ignore:
            for s in itertext(e, ignore=ignore):
                yield s
            if e.tail:
                yield e.tail

