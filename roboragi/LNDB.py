'''
LNDB.py
Handles all LNDB information
'''

import difflib

import aiohttp
from pyquery import PyQuery as pq

session = aiohttp.ClientSession()


async def getLightNovelURL(searchText):
    try:
        searchText = searchText.replace(' ', '+')
        async with session.get('http://lndb.info/search?text=' + searchText,
                               timeout=10) as resp:
            html = await resp.text()

        lndb = pq(html)

        lnList = []

        if 'light_novel' in html.url:
            # we've immediately hit a result
            return html.url
        else:
            # scan the search page for stuff

            lnList = []

            for thing in lndb.find('#bodylightnovelscontentid table tr'):
                title = pq(thing).find('a').text()
                url = pq(thing).find('a').attr('href')

                if title:
                    data = {'title': title,
                            'url': url}
                    lnList.append(data)

            closest = findClosestLightNovel(searchText, lnList)
            return closest['url']

    except Exception as e:
        return None


def findClosestLightNovel(searchText, lnList):
    try:
        nameList = []

        for ln in lnList:
            nameList.append(ln['title'].lower())

        closestNameFromList = difflib.get_close_matches(searchText.lower(),
                                                        nameList, 1, 0.80)

        for ln in lnList:
            if ln['title'].lower() == closestNameFromList[0].lower():
                return ln

        return None
    except:
        return None


def getLightNovelById(lnId):
    return 'http://lndb.info/light_novel/' + str(lnId)
