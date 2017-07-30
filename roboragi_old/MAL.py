# -*- coding: utf-8 -*-

"""
MAL.py
Handles all of the connections to MyAnimeList.
"""

import difflib
import traceback
import urllib
import xml.etree.cElementTree as ET

import aiohttp

import roboragi_old.DatabaseHandler as DatabaseHandler

try:
    import roboragi_old.Config as Config

    print('Setting up MAL Connection')
    MALUSERAGENT = Config.maluseragent
    MALAUTH = Config.malauth
except ImportError:
    pass

try:
    mal = aiohttp.ClientSession(
        headers={'Authorization': MALAUTH, 'User-Agent': MALUSERAGENT})
except Exception as e:
    print(e)


# Sets up the connection to MAL.
def setup():
    mal = aiohttp.ClientSession(
        headers={'Authorization': MALAUTH, 'User-Agent': MALUSERAGENT})


def getSynonyms(request):
    synonyms = []

    synonyms.append(request['title']) if request['title'] else None
    synonyms.append(request['english']) if request['english'] else None
    synonyms.extend(request['synonyms']) if request['synonyms'] else None

    return synonyms


# Returns the closest anime (as a Json-like object) it can find using the given searchtext. MAL returns XML (bleh) so we have to convert it ourselves.
async def getAnimeDetails(searchText, animeId=None):
    cachedAnime = DatabaseHandler.checkForMalEntry('malanime', searchText,
                                                   animeId)
    if cachedAnime is not None:
        if cachedAnime['update']:
            print("found cached anime, needs update in mal")
            pass
        else:
            print("found cached anime, doesn't need update in mal")
            return cachedAnime['content']

    cleanSearchText = urllib.parse.quote(searchText)
    try:
        try:
            async with mal.get(
                            'https://myanimelist.net/api/anime/search.xml?q=' + cleanSearchText.rstrip(),
                            timeout=10) as resp:
                if resp.status != 200:
                    print("Searching for {} failed with error code {}".format(
                        searchText.rstrip(), resp.status))
                request = await resp.text()
        except Exception as e:
            print(e)
            setup()
            try:
                async with mal.get(
                                'https://myanimelist.net/api/anime/search.xml?q=' + searchText.rstrip(),
                                timeout=10) as resp:
                    request = await resp.text()
            except aiohttp.exceptions.RequestException as e:  # This is the correct syntax
                print(e)

                # convertedRequest = convertShittyXML(request)
        rawList = ET.fromstring(request)

        animeList = []

        for anime in rawList.findall('./entry'):
            animeID = anime.find('id').text
            title = anime.find('title').text
            title_english = anime.find('english').text

            synonyms = None
            if anime.find('synonyms').text is not None:
                synonyms = anime.find('synonyms').text.split(";")

            episodes = anime.find('episodes').text
            animeType = anime.find('type').text
            status = anime.find('status').text
            start_date = anime.find('start_date').text
            end_date = anime.find('end_date').text
            synopsis = anime.find('synopsis').text
            image = anime.find('image').text

            data = {'id': animeID,
                    'title': title,
                    'english': title_english,
                    'synonyms': synonyms,
                    'episodes': episodes,
                    'type': animeType,
                    'status': status,
                    'start_date': start_date,
                    'end_date': end_date,
                    'synopsis': synopsis,
                    'image': image}

            animeList.append(data)

        if animeId:
            closestAnime = getThingById(animeId, animeList)
        elif cachedAnime and cachedAnime['update']:
            closestAnime = getThingById(cachedAnime['id'], animeList)
        else:
            closestAnime = getClosestAnime(searchText.strip(), animeList)

        return closestAnime

    except Exception as e:
        print("Error finding anime:{} on MAL\nError:{}".format(searchText, e))
        # traceback.print_exc()

        return None


# Given a list, it finds the closest anime series it can.
def getClosestAnime(searchText, animeList):
    try:
        nameList = []
        for anime in animeList:
            nameList.append(anime['title'].lower().strip())

            if anime['english'] is not None:
                nameList.append(anime['english'].lower().strip())

            if anime['synonyms']:
                for synonym in anime['synonyms']:
                    nameList.append(synonym.lower().strip())

        closestNameFromList = \
        difflib.get_close_matches(searchText.lower(), nameList, cutoff=0.90)[0]

        for anime in animeList:
            if anime['title']:
                if anime['title'].lower() == closestNameFromList.lower():
                    return anime
            elif anime['english']:
                if anime['english'].lower() == closestNameFromList.lower():
                    return anime
            else:
                for synonym in anime['synonyms']:
                    if synonym.lower() == closestNameFromList.lower():
                        return anime

        return None
    except Exception:
        # print("Error finding anime:{} on MAL\nError:{}".format(searchText, e))
        # traceback.print_exc()
        return None


# MAL's XML is a piece of crap. It needs to be escaped twice because they do shit like this: &amp;sup2;
def convertShittyXML(text):
    # It pains me to write shitty code, but MAL needs to improve their API and I'm sick of not being able to parse shit
    text = text.replace('&Eacute;', 'É').replace('&times;', 'x').replace(
        '&rsquo;', "'").replace('&lsquo;', "'").replace('&hellip',
                                                        '...').replace('&le',
                                                                       '<').replace(
        '<;', '; ').replace('&hearts;', '♥').replace('&mdash;', '-')
    text = text.replace('&eacute;', 'é').replace('&ndash;', '-').replace(
        '&Aacute;', 'Á').replace('&acute;', 'à').replace('&ldquo;',
                                                         '"').replace(
        '&rdquo;', '"').replace('&Oslash;', 'Ø').replace('&frac12;',
                                                         '½').replace(
        '&infin;', '∞')
    text = text.replace('&agrave;', 'à').replace('&egrave;', 'è').replace(
        '&dagger;', '†').replace('&sup2;', '²').replace('&#039;', "'")

    # text = text.replace('&', '&amp;')

    return text

    text = html.parser.HTMLParser().unescape(text)
    return html.parser.HTMLParser().unescape(text)


# Used to check if two descriptions are relatively close. This is used in place of author searching because MAL don't give authors at any point.
def getClosestFromDescription(mangaList, descriptionToCheck):
    try:
        descList = []
        for manga in mangaList:
            descList.append(manga['synopsis'].lower())

        closestNameFromList = \
        difflib.get_close_matches(descriptionToCheck.lower(), descList, 1,
                                  0.1)[0]

        for manga in mangaList:
            if closestNameFromList == manga['synopsis'].lower():
                return manga

    except:
        return None


# Since MAL doesn't give me an author, I make a search using similar descriptions instead. Super janky.
async def getMangaCloseToDescription(searchText, descriptionToCheck):
    cleanSearchText = urllib.parse.quote(searchText)
    try:
        try:
            async with mal.get(
                            'https://myanimelist.net/api/manga/search.xml?q=' + cleanSearchText.rstrip(),
                            timeout=10) as resp:
                request = await resp.text()

        except:
            setup()
            async with mal.get(
                            'https://myanimelist.net/api/manga/search.xml?q=' + cleanSearchText.rstrip(),
                            timeout=10) as resp:
                request = await resp.text()

        convertedRequest = convertShittyXML(request)
        # print(convertedRequest)
        rawList = ET.fromstring(convertedRequest)

        mangaList = []

        for manga in rawList.findall('./entry'):
            mangaId = manga.find('id').text
            title = manga.find('title').text
            title_english = manga.find('english').text

            synonyms = None
            if manga.find('synonyms').text is not None:
                synonyms = manga.find('synonyms').text.split(";")

            chapters = manga.find('chapters').text
            volumes = manga.find('volumes').text
            mangaType = manga.find('type').text
            status = manga.find('status').text
            start_date = manga.find('start_date').text
            end_date = manga.find('end_date').text
            synopsis = manga.find('synopsis').text
            image = manga.find('image').text

            data = {'id': mangaId,
                    'title': title,
                    'english': title_english,
                    'synonyms': synonyms,
                    'chapters': chapters,
                    'volumes': volumes,
                    'type': mangaType,
                    'status': status,
                    'start_date': start_date,
                    'end_date': end_date,
                    'synopsis': synopsis,
                    'image': image}

            mangaList.append(data)

        closeManga = getListOfCloseManga(searchText, mangaList)

        return getClosestFromDescription(closeManga, descriptionToCheck)
    except:
        print("Error finding manga:{} on MAL\nError:{}".format(searchText, e))
        # traceback.print_exc()
        return None


async def getLightNovelDetails(searchText, lnId=None):
    return await getMangaDetails(searchText, lnId, True)


# Returns the closest manga series given a specific search term. Again, MAL returns XML, so we conver it ourselves
async def getMangaDetails(searchText, mangaId=None, isLN=False):
    cachedManga = DatabaseHandler.checkForMalEntry('malmanga', searchText,
                                                   mangaId, isLN)
    if cachedManga is not None:
        if cachedManga['update']:
            print("found cached anime, needs update in mal")
            pass
        else:
            print("found cached anime, doesn't need update in mal")
            return cachedManga['content']
    cleanSearchText = urllib.parse.quote(searchText)
    try:
        try:
            async with mal.get(
                            'https://myanimelist.net/api/manga/search.xml?q=' + cleanSearchText.rstrip(),
                            timeout=10) as resp:
                request = await resp.text()

        except Exception as e:
            print(e)
            setup()
            async with mal.get(
                            'https://myanimelist.net/api/manga/search.xml?q=' + cleanSearchText.rstrip(),
                            timeout=10) as resp:
                request = await resp.text()

        # convertedRequest = convertShittyXML(request)
        rawList = ET.fromstring(request)
        # print(convertedRequest)

        mangaList = []

        for manga in rawList.findall('./entry'):
            newMangaId = manga.find('id').text
            title = manga.find('title').text
            title_english = manga.find('english').text

            synonyms = None
            if manga.find('synonyms').text is not None:
                synonyms = manga.find('synonyms').text.split(";")

            chapters = manga.find('chapters').text
            volumes = manga.find('volumes').text
            mangaType = manga.find('type').text
            status = manga.find('status').text
            start_date = manga.find('start_date').text
            end_date = manga.find('end_date').text
            synopsis = manga.find('synopsis').text
            image = manga.find('image').text

            data = {'id': newMangaId,
                    'title': title,
                    'english': title_english,
                    'synonyms': synonyms,
                    'chapters': chapters,
                    'volumes': volumes,
                    'type': mangaType,
                    'status': status,
                    'start_date': start_date,
                    'end_date': end_date,
                    'synopsis': synopsis,
                    'image': image}

            # print(data['title'])
            # ignore or allow LNs
            if 'novel' in mangaType.lower():
                if isLN:
                    mangaList.append(data)
            else:
                if not isLN:
                    mangaList.append(data)
        # print(mangaId)
        if mangaId:
            closestManga = getThingById(mangaId, mangaList)
        elif cachedManga and cachedManga['update']:
            closestManga = getThingById(cachedManga['id'], mangaList)
        else:
            closestManga = getClosestManga(searchText.strip(), mangaList)

        if closestManga:
            return closestManga
        else:
            return None

    except Exception as e:
        print("Error finding manga:{} on MAL\nError:{}".format(searchText, e))
        # traceback.print_exc()
        return None


# Returns a list of manga with titles very close to the search text. Current unused because MAL's API is shit and doesn't return author names.
def getListOfCloseManga(searchText, mangaList):
    try:
        ratio = 0.90
        returnList = []

        for manga in mangaList:
            if round(difflib.SequenceMatcher(lambda x: x == "",
                                             manga['title'].lower(),
                                             searchText.lower()).ratio(),
                     3) >= ratio:
                returnList.append(manga)
            elif manga['english'] is not None:
                if round(difflib.SequenceMatcher(lambda x: x == "",
                                                 manga['english'].lower(),
                                                 searchText.lower()).ratio(),
                         3) >= ratio:
                    returnList.append(manga)
            elif manga['synonyms'] is not None:
                for synonym in manga['synonyms']:
                    if round(
                            difflib.SequenceMatcher(lambda x: x == "", synonym,
                                                    searchText.lower()).ratio(),
                            3) >= ratio:
                        returnList.append(manga)
                        break

        return returnList

    except Exception:
        traceback.print_exc()
        return None


# Used to determine the closest manga to a given search term in a list
def getClosestManga(searchText, mangaList):
    try:
        nameList = []

        for manga in mangaList:
            nameList.append(manga['title'].lower().strip())

            if manga['english'] is not None:
                nameList.append(manga['english'].lower().strip())

            if manga['synonyms'] is not None:
                for synonym in manga['synonyms']:
                    nameList.append(synonym.lower().strip())
        # print(searchText)
        closestNameFromList = \
        difflib.get_close_matches(searchText.lower().strip(), nameList, 1,
                                  0.90)[0]
        # print(closestNameFromList)
        for manga in mangaList:
            if manga['title'].lower() == closestNameFromList.lower():
                return manga
            elif manga['english'] is not None:
                if manga['english'].lower() == closestNameFromList.lower():
                    return manga

        for manga in mangaList:
            if manga['synonyms'] is not None:
                for synonym in manga['synonyms']:
                    if synonym.lower().strip() == closestNameFromList.lower():
                        return manga

        return None
    except Exception as e:
        # print("Error finding manga:{} on MAL\nError:{}".format(searchText, e))
        # traceback.print_exc()
        return None


# Used to find thing by an id
def getThingById(thingId, thingList):
    try:
        for thing in thingList:
            if int(thing['id']) == int(thingId):
                return thing

        return None
    except Exception:
        traceback.print_exc()
        return None


setup()
