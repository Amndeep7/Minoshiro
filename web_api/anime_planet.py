"""
Retrieve anime info from AnimePlanet.
"""

from difflib import SequenceMatcher
from typing import List, Optional
from urllib.parse import quote
from pyquery import PyQuery

def sanitize_search_text(text:str) -> str:
    """
    Sanitize text for Anime-Planet use.
    :param text: the text to be escaped.
    :return: the escaped text.
    """
    return text.replace('(TV)', 'TV')

async def get_anime_url(
        session_manager: SessionManager, query: str) -> Optional[str]:
    """
    Get anime url by search query.
    :param session_manager: the `SessionManager` instance.
    :param query: a search query.
    :return: the anime url if it's found.
    """
    query = sanitize_search_text(query)
    params = {
        'query': quote(query)
    }
    try:
        async with await session_manager.get("http://www.anime-planet.com/anime/all?", params=params) as resp:
            html = await resp.text()
        ap = PyQuery(html)
    except Exception as e:
        session_manager.logger.warn(str(e))
        return

    if ap.find('.cardDeck.pure-g.cd-narrow[data-type="anime"]'):
        anime_list = []
        for entry in ap.find('.card.pure-1-6'):
            anime = {
                'title': PyQuery(entry).find('h4').text()
                'url': f'http://www.anime-planet.com{PyQuery(entry).find('a').attr('href')}'
            }
            anime_list.append(anime)
        return __get_closest(query, anime_list).get('url')
    else:
        return ap.find("meta[property='og:url']").attr('content')
    
    return None


def __get_closest(query: str, anime_list: List[dict]) -> dict:
    """
    Get the closest matching anime by search query.
    :param query: the search term.
    :param anime_list: a list of animes.

    :return:
        Closest matching anime by search query if found else an empty dict.
    """
    max_ratio, match = 0, None
    matcher = SequenceMatcher(b=query.lower())
    for anime in anime_list:
        ratio = __match_max(anime, matcher)
        if ratio > max_ratio and ratio >= 0.85:
            max_ratio = ratio
            match = anime
    return match or {}

def __match_max(anime: dict, matcher: SequenceMatcher) -> float:
    """
    Get the max matched ratio for a given anime.

    :param anime: the anime.

    :param matcher: the `SequenceMatcher` with the search query as seq2.

    :return: the max matched ratio.
    """
    max_ratio = 0
    for title in anime['titles']:
        matcher.set_seq1(title['title'].lower())
        ratio = matcher.ratio()
        if ratio > max_ratio:
            max_ratio = ratio
    return max_ratio
