from enum import EnumMeta
from inspect import iscoroutinefunction

from minoshiro import DataController, Medium, PostgresController, Minoshiro, \
    Site, SqliteController
from minoshiro.utils.pre_cache import cache_top_pages


def test_imports():
    assert isinstance(Minoshiro, type)
    assert isinstance(DataController, type)
    assert isinstance(PostgresController, type)
    assert isinstance(SqliteController, type)
    assert PostgresController in DataController.__subclasses__()
    assert SqliteController in DataController.__subclasses__()
    assert isinstance(Site, EnumMeta)
    assert isinstance(Medium, EnumMeta)
    assert iscoroutinefunction(cache_top_pages)
