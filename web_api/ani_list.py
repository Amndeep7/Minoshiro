from itertools import chain
from typing import List, Optional
from urllib.parse import quote
from difflib import SequenceMatcher
from session_manager import HTTPStatusError, SessionManager

__escape_table = {
    '&': ' ',
    "\'": "\\'",
    '\"': '\\"',
    '/': ' ',
    '-': ' '
    # '!': '\!'
}


def escape(text: str) -> str:
    """
    Escape text for ani list use.
    :param text: the text to be escaped.
    :return: the escaped text.
    """
    return ''.join(__escape_table.get(c, c) for c in text)


def get_synonyms(request: dict):
    """
    Get all synonyms from a request.
    :param request: the request data.
    :return: all synonyms form the request.
    """
    iterator = chain(
        (request.get('title_english'), request.get('title_romaji')),
        request.get('synonyms', ())
    )
    return [s for s in iterator if s]


class AniList:
    """
    Since we need a new access token from Anilist every hour, a class is more
    appropriate to handle ani list searches.
    """

    def __init__(self, session_manager: SessionManager, client_id: str,
                 client_secret: str):
        """
        Init the class.
        :param client_id: the Anilist client id.
        :param client_secret: the Anilist client secret.
        """
        self.access_token = None
        self.client_id = client_id
        self.client_secret = client_secret
        self.session_manager = session_manager
        self.base_url = 'https://anilist.co/api'

    async def get_token(self) -> Optional[str]:
        """
        Get an access token from Anilist.
        :return: the access token if success.
        """
        params = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        try:
            resp = await self.session_manager.post(
                f'{self.base_url}/auth/access_token',
                params=params
            )
        except HTTPStatusError as e:
            self.session_manager.logger.warn(str(e))
            return
        async with resp:
            js = await resp.json()
            return js.get('access_token')

    async def get_entry_details(
            self,
            session_manager: SessionManager,
            medium: str,
            query: str,
            thing_id: str=None) -> Optional[dict]:
        """
        Get the details of an thing by search query.
        :param session_manager: session manager object
        :param medium: medium to search for 'anime', 'manga', 'novel'
        :param query: the search term.
        :param thing_id: thing id.
        :return: dict with thing info.
        """
        self.access_token = await self.get_token()
        clean_query = escape(query)
        params = {
            'access_token': self.access_token
        }
        try:
            if medium == 'novel':
                url = f'{self.base_url}/manga/search/{quote(clean_query)}'
            else:
                url = f'{self.base_url}/{medium}/search/{quote(clean_query)}'

            print(url)
            async with await session_manager.get(url, params=params) as resp:
                if resp.status != 200:
                    token = await self.get_token()
                    async with await session_manager.get(
                            url,
                            params={'access_token': token}) as resp:
                        thing = await resp.json()
                else:
                    thing = await resp.json()
        except Exception as e:
            session_manager.logger.warn(str(e))
            return
        for entry in thing:
            if medium == 'manga' and 'novel' in entry['type'].lower():
                thing.remove(entry)
            elif medium == 'novel' and 'novel' not in entry['type'].lower():
                thing.remove(entry)
        return self.__get_closest(query, thing)

    def __get_closest(self, query: str, thing_list: List[dict]) -> dict:
        """
        Get the closest matching anime by search query.
        :param query: the search term.
        :param thing_list: a list of animes.
        :return: Closest matching anime by search query if found
                    else an empty dict.
        """
        max_ratio, match = 0, None
        matcher = SequenceMatcher(b=query.lower().strip())
        for thing in thing_list:
            ratio = self.__match_max(thing, matcher)
            if ratio > max_ratio and ratio >= 0.90:
                max_ratio = ratio
                match = thing
        return match or {}

    def __match_max(self, thing: dict, matcher: SequenceMatcher) -> float:
        """
        Get the max matched ratio for a given thing.
        :param thing: the thing.
        :param matcher: the `SequenceMatcher` with the search query as seq2.
        :return: the max matched ratio.
        """
        thing_name_list = []
        thing_name_list_no_syn = []
        max_ratio = 0
        if 'title_english' in thing:
            thing_name_list.append(thing['title_english'].lower())
            thing_name_list_no_syn.append(thing['title_english'].lower())

        if 'title_romaji' in thing:
            thing_name_list.append(thing['title_romaji'].lower())
            thing_name_list_no_syn.append(thing['title_romaji'].lower())

        if 'synonyms' in thing:
            for synonym in thing['synonyms']:
                    thing_name_list.append(synonym.lower())

        for name in thing_name_list:
            matcher.set_seq1(name.lower())
            ratio = matcher.ratio()
            if ('one shot' in thing['type'].lower()):
                ratio = ratio - .05
            if ratio > max_ratio:
                max_ratio = ratio
            if thing['synonyms']:
                for synonym in thing['synonyms']:
                    matcher.set_seq1(synonym.lower())
                    ratio = matcher.ratio()
                    if ratio > max_ratio:
                        max_ratio = ratio
        return max_ratio
