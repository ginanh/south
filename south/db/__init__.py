
# Establish the common DatabaseOperations instance, which we call 'db'.
# Much thanks to cmkmrr for a lot of the code base here

from django.conf import settings
import sys

# A few aliases, because there's FQMNs now
engine_modules = {
    'django.db.backends.postgresql_psycopg2': 'postgresql_psycopg2',
    'django.db.backends.sqlite3': 'sqlite3',
    'django.db.backends.mysql': 'mysql',
    'django.db.backends.oracle': 'oracle',
    'sql_server.pyodbc': 'sql_server.pyodbc', #django-pyodbc
    'sqlserver_ado': 'sql_server.pyodbc', #django-mssql
    'django.contrib.gis.db.backends.postgis': 'postgresql_psycopg2',
    'django.contrib.gis.db.backends.spatialite': 'sqlite3',
    'django.contrib.gis.db.backends.mysql': 'mysql',
    'django.contrib.gis.db.backends.oracle': 'oracle',
}

# First, work out if we're multi-db or not, and which databases we have
try: 
    from django.db import DEFAULT_DB_ALIAS 
except ImportError:
    #### 1.1 or below ####
    # We'll 'fake' multi-db; set the default alias
    DEFAULT_DB_ALIAS = 'default'
    # SOUTH_DATABASE_ADAPTER is an optional override if you have a different module
    engine = getattr(settings, "SOUTH_DATABASE_ADAPTER", "south.db.%s" % settings.DATABASE_ENGINE)
    # And then, we have one database with one engine
    db_engines = {DEFAULT_DB_ALIAS: engine}
else:
    #### 1.2 or above ####
    # Loop over the defined databases, gathering up their engines
    db_engines = dict([
        # Note we check to see if contrib.gis has overridden us.
        (alias, "south.db.%s" % engine_modules.get(db_settings['ENGINE'], None))
        for alias, db_settings in settings.DATABASES.items()
    ])
    # Update with any overrides
    db_engines.update(getattr(settings, "SOUTH_DATABASE_ADAPTERS", {}))
    # Check there's no None engines, or...
    for alias, engine in db_engines.items():
        if engine is None:
            # They've used a backend we don't support
            sys.stderr.write(
                (
                    "There is no South database module for your database backend '%s'. " + \
                    "Please either choose a supported database, check for " + \
                    "SOUTH_DATABASE_ADAPTER[S] settings, " + \
                    "or remove South from INSTALLED_APPS.\n"
                ) % (settings.DATABASES[alias]['ENGINE'],)
            )
            sys.exit(1)


class LazyDBRegistry(dict):
    def __missing__(self, alias):
        ops = module.DatabaseOperations(alias)
        self[alias] = ops
        return ops

# Now, turn that into a dict of <alias: south db module>
dbs = LazyDBRegistry()

try:
    for _, module_name in db_engines.items():
        module = __import__(module_name, {}, {}, [''])
except ImportError:
    # This error should only be triggered on 1.1 and below.
    sys.stderr.write(
        (
            "There is no South database module '%s' for your database. " + \
            "Please either choose a supported database, check for " + \
            "SOUTH_DATABASE_ADAPTER[S] settings, " + \
            "or remove South from INSTALLED_APPS.\n"
        ) % (module_name,)
    )
    sys.exit(1)

# Finally, to make old migrations work, keep 'db' around as the default database
db = dbs[DEFAULT_DB_ALIAS]
