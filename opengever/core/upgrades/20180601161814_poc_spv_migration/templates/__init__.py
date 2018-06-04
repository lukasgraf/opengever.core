from pkg_resources import resource_string


def load(filename):
    return resource_string(
        'opengever.core.upgrades.20180601161814_poc_spv_migration.templates',
        filename)
