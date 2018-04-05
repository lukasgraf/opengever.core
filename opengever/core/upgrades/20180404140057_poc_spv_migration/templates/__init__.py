from pkg_resources import resource_string


def load(filename):
    return resource_string(
        'opengever.core.upgrades.20180404140057_poc_spv_migration.templates',
        filename)
