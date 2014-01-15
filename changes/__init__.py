try:
    VERSION = __import__('pkg_resources') \
        .get_distribution('changes').version
except Exception, e:
    VERSION = 'unknown'
