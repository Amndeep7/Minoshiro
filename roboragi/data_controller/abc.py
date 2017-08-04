from abc import abstractmethod
from json import loads
from typing import Dict, Optional

from .data_utils import get_all_synonyms
from .enums import Medium, Site

_convert_medium = {
    'Anime': Medium.ANIME,
    'Manga': Medium.MANGA,
    'LN': Medium.LN
}


class DataController:
    """
    An ABC for all classes that deals with database read write.
    """
    __slots__ = ('logger',)

    def __init__(self, logger):
        """
        :param logger: the logger object to do logging with.
        """
        self.logger = logger

    @abstractmethod
    async def get_identifier(self, query: str,
                             medium: Medium) -> Optional[Dict[Site, str]]:
        """
        Get the identifier of a given search query.

        :param query: the search query.

        :param medium: the medium type.

        :return: A dict of all identifiers for this search query for all sites,
                 None if nothing is found.
        """
        raise NotImplementedError

    @abstractmethod
    async def set_identifier(self, name: str, medium: Medium,
                             site: Site, identifier: str):
        """
        Set the identifier for a given name.

        :param name: the name.

        :param medium: the medium type.

        :param site: the site.

        :param identifier: the identifier.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_mal_title(self, id_: str, medium: Medium) -> Optional[str]:
        """
        Get a MAL title by its id.
        :param id_: th MAL id.
        :param medium: the medium type.
        :return: The MAL title if it's found.
        """
        raise NotImplementedError

    @abstractmethod
    async def set_mal_title(self, id_: str, medium: Medium, title: str):
        """
        Set the MAL title for a given id.
        :param id_: the MAL id.

        :param medium: The medium type.

        :param title: The MAL title for the given id.
        """
        raise NotImplementedError

    @abstractmethod
    async def medium_data_by_id(self, id_: str, medium: Medium,
                                site: Site) -> Optional[dict]:
        """
        Get data by id.
        :param id_: the id.
        :param medium: the medium type.
        :param site: the site.
        :return: the data for that id if found.
        """
        raise NotImplementedError

    @abstractmethod
    async def set_medium_data(self, id_: str, medium: Medium,
                              site: Site, data: dict):
        """
        Set the data for a given id.

        :param id_: the id.

        :param medium: the medium type.

        :param site: the site.

        :param data: the data for the id.
        """
        raise NotImplementedError

    async def get_medium_data(self, query: str,
                              medium: Medium) -> Optional[dict]:
        """
        Get the cached data for the given search query.

        :param query: the search query.

        :param medium: the medium type.

        :return: the cached data, for all sites that has the data.
        """
        id_dict = await self.get_identifier(query, medium)
        if not id_dict:
            return
        return {site: data for site, data in {
            site: await self.medium_data_by_id(id_, medium, site)
            for site, id_ in id_dict.items()
        }.items() if data}

    async def pre_cache(self):
        """
        Populate the lookup with synonyms.
        """
        rows = get_all_synonyms()
        for name, type_, db_links in rows:
            dict_ = loads(db_links)
            mal_name, mal_id = dict_.get('mal', ('', ''))
            anilist = dict_.get('ani')
            ap = dict_.get('ap')
            anidb = dict_.get('adb')
            medium = _convert_medium[type_]
            if mal_name and mal_id:
                await self.set_mal_title(str(mal_id), medium, str(mal_name))
            await self.__precache_one(name, medium, Site.MAL, mal_id)
            await self.__precache_one(name, medium, Site.ANILIST, anilist)
            await self.__precache_one(name, medium, Site.ANIMEPLANET, ap)
            await self.__precache_one(name, medium, Site.ANIDB, anidb)

    async def __precache_one(self, name, medium, site, id_):
        if name and (id_ or isinstance(id_, int)):
            await self.set_identifier(str(name), medium, site, str(id_))
