'''
AniDB.py
Handles all AniDB information
'''

import difflib
import traceback
import urllib

import aiohttp
from pyquery import PyQuery as pq

session = aiohttp.ClientSession()


async def getAnimeURL(searchText):
    cleanSearchText = urllib.parse.quote(searchText)
    try:
        async with session.get(
                        'http://anisearch.outrance.pl/?task=search&query=' + cleanSearchText,
                        timeout=10) as resp:
            html = await resp.read()
            anidb = pq(html)
    except:
        traceback.print_exc()
        return None

    animeList = []

    for anime in anidb('animetitles anime'):
        titles = []
        for title in pq(anime).find('title').items():
            titleInfo = {}
            titleInfo['title'] = title.text()
            titleInfo['lang'] = title.attr['lang']
            titles.append(titleInfo)

        url = 'http://anidb.net/a' + anime.attrib['aid']

        if titles:
            data = {'titles': titles,
                    'url': url
                    }

            animeList.append(data)

    closest = getClosestAnime(searchText, animeList)

    if closest:
        return closest['url']
    else:
        return None


def getAnimeURLById(animeId):
    return 'http://anidb.net/a' + str(animeId)


def getClosestAnime(searchText, animeList):
    nameList = []

    trustedNames = []  # i.e. English/default names
    untrustedNames = []  # everything else (French, Italian etc)

    for anime in animeList:
        for title in anime['titles']:
            if title['lang'].lower() in ['x-jat', 'en']:
                trustedNames.append(title['title'].lower())
            else:
                untrustedNames.append(title['title'].lower())

    closestNameFromList = difflib.get_close_matches(searchText.lower(),
                                                    trustedNames, 1, 0.85)

    if closestNameFromList:
        for anime in animeList:
            for title in anime['titles']:
                if closestNameFromList[0].lower() == title['title'].lower() and \
                                title['lang'].lower() in ['x-jat', 'en']:
                    return anime
    else:
        closestNameFromList = difflib.get_close_matches(searchText.lower(),
                                                        untrustedNames, 1,
                                                        0.85)

        if closestNameFromList:
            for anime in animeList:
                for title in anime['titles']:
                    if closestNameFromList[0].lower() == title[
                        'title'].lower() and title['lang'].lower() not in [
                        'x-jat', 'en']:
                        return anime

    return None
