'''
DiscordoragiSearch .py
Returns a built comment created from multiple databases when given a search term.
'''

import json
import sqlite3
import traceback

import roboragi_old.AniDB as AniDB
import roboragi_old.Anilist as Anilist
import roboragi_old.AnimePlanet as AniP
import roboragi_old.CommentBuilder as CommentBuilder
import roboragi_old.DatabaseHandler as DatabaseHandler
import roboragi_old.LNDB as LNDB
import roboragi_old.MAL as MAL
import roboragi_old.MU as MU
import roboragi_old.NU as NU

USERNAME = ''

try:
    import Config

    USERNAME = Config.username
except ImportError:
    pass

sqlConn = sqlite3.connect('synonyms.db')
sqlCur = sqlConn.cursor()

try:
    sqlCur.execute(
        'SELECT dbLinks FROM synonyms WHERE type = "Manga" AND lower(name) = ?',
        ["despair simulator"])
except sqlite3.Error:
    traceback.print_exc()


# Checks if the message is valid (i.e. not already seen, not a post by Roboragi and the parent commenter isn't Roboragi)
def isValidMessage(message):
    try:
        if (DatabaseHandler.messageExists(message.id)):
            return False

        try:
            if (message.author.name == USERNAME):
                DatabaseHandler.addMessage(message.id, message.author.id,
                                           message.server.id, False)
                return False
        except:
            pass

        return True

    except:
        traceback.print_exc()
        return False


# Builds a manga reply from multiple sources
async def buildMangaReply(searchText, message, isExpanded, canEmbed,
                          blockTracking=False):
    try:
        ani = None
        mal = None
        mu = None
        ap = None

        try:
            sqlCur.execute(
                'SELECT dbLinks FROM synonyms WHERE type = "Manga" AND lower(name) = ?',
                [searchText.lower()])
        except sqlite3.Error as e:
            print(e)

        alternateLinks = sqlCur.fetchone()

        if (alternateLinks):
            synonym = json.loads(alternateLinks[0])

            if 'mal' in synonym:
                if (synonym['mal']):
                    mal = await roboragi.MAL as MAL.getMangaDetails(
                        synonym['mal'][0], synonym['mal'][1])

            if 'ani' in synonym:
                if (synonym['ani']):
                    ani = await Anilist.getMangaDetailsById(synonym['ani'])

            if 'mu' in synonym:
                if (synonym['mu']):
                    mu = MU.getMangaURLById(synonym['mu'])

            if 'ap' in synonym:
                if (synonym['ap']):
                    ap = AniP.getMangaURLById(synonym['ap'])

        else:
            # Basic breakdown:
            # If Anilist finds something, use it to find the MAL version.
            # If hits either MAL or Ani, use it to find the MU version.
            # If it hits either, add it to the request-tracking DB.
            ani = await Anilist.getMangaDetails(searchText)

            if ani:
                try:
                    mal = await roboragi.MAL as MAL.getMangaDetails(
                        ani['title_romaji'])
                except Exception as e:
                    print(e)
                    pass

                if not mal:
                    try:
                        mal = await roboragi.MAL as MAL.getMangaDetails(
                            ani['title_english'])
                    except:
                        pass

                if not mal:
                    mal = await roboragi.MAL as MAL.getMangaDetails(searchText)

            else:
                mal = await roboragi.MAL as MAL.getMangaDetails(searchText)

                if mal:
                    ani = await Anilist.getMangaDetails(mal['title'])

                    # ----- Finally... -----#
        if ani or mal:
            try:
                titleToAdd = ''
                if mal:
                    titleToAdd = mal['title']
                else:
                    try:
                        titleToAdd = ani['title_english']
                    except:
                        titleToAdd = ani['title_romaji']

                if not alternateLinks:
                    # MU stuff
                    if mal:
                        mu = await MU.getMangaURL(mal['title'])
                    else:
                        mu = await MU.getMangaURL(ani['title_romaji'])

                    # Do the anime-planet stuff
                    if mal and not ap:
                        if mal['title'] and not ap:
                            ap = await AniP.getMangaURL(mal['title'])
                        if mal['english'] and not ap:
                            ap = await AniP.getMangaURL(mal['english'])
                        if mal['synonyms'] and not ap:
                            for synonym in mal['synonyms']:
                                if ap:
                                    break
                                ap = await AniP.getMangaURL(synonym)

                    if ani and not ap:
                        if ani['title_english'] and not ap:
                            ap = await AniP.getMangaURL(ani['title_english'])
                        if ani['title_romaji'] and not ap:
                            ap = await AniP.getMangaURL(ani['title_romaji'])
                        if ani['synonyms'] and not ap:
                            for synonym in ani['synonyms']:
                                if ap:
                                    break
                                ap = await AniP.getMangaURL(synonym)
                if not blockTracking:
                    DatabaseHandler.addRequest(titleToAdd, 'Manga',
                                               message.author.id,
                                               message.server.id)
            except:
                traceback.print_exc()
                pass
        if mal:
            try:
                DatabaseHandler.addMalEntry('malmanga', mal)
            except:
                traceback.print_exc()
                pass
        if ani:
            try:
                DatabaseHandler.addAniEntry('anilistmanga', ani)
            except:
                traceback.print_exc()
                pass
        if not canEmbed:
            return CommentBuilder.buildMangaComment(isExpanded, mal, ani, mu,
                                                    ap)
        else:
            return CommentBuilder.buildMangaEmbed(isExpanded, mal, ani, mu, ap)
    except Exception as e:
        traceback.print_exc()
        return None


# Builds a manga search for a specific series by a specific author
async def buildMangaReplyWithAuthor(searchText, authorName, message,
                                    isExpanded, canEmbed, blockTracking=False):
    try:
        ani = await Anilist.getMangaWithAuthor(searchText, authorName)
        mal = None
        mu = None
        ap = None

        if ani:
            try:
                mal = await roboragi.MAL as MAL.getMangaCloseToDescription(
                    searchText, ani['description'])
                ap = await AniP.getMangaURL(ani['title_english'], authorName)
            except Exception as e:
                print(e)
        else:
            ap = await AniP.getMangaURL(searchText, authorName)

        mu = await MU.getMangaWithAuthor(searchText, authorName)

        if ani:
            try:
                titleToAdd = ''
                if mal is not None:
                    titleToAdd = mal['title']
                else:
                    titleToAdd = ani['title_english']

                if not blockTracking:
                    DatabaseHandler.addRequest(titleToAdd, 'Manga',
                                               message.author.id,
                                               message.server.id)
            except:
                traceback.print_exc()
                pass

            if not canEmbed:
                return CommentBuilder.buildMangaComment(isExpanded, mal, ani,
                                                        mu, ap)
            else:
                return CommentBuilder.buildMangaEmbed(isExpanded, mal, ani, mu,
                                                      ap)

    except Exception as e:
        traceback.print_exc()
        return None


# Builds an anime reply from multiple sources
async def buildAnimeReply(searchText, message, isExpanded, canEmbed,
                          blockTracking=False):
    try:
        mal = {'search_function': roboragi.MAL as MAL.getAnimeDetails,
                                                  'synonym_function': roboragi.MAL as MAL.getSynonyms,
                                                                                      'checked_synonyms': [],
        'result': None}
        ani = {'search_function': Anilist.getAnimeDetails,
               'synonym_function': Anilist.getSynonyms,
               'checked_synonyms': [],
               'result': None}
        ap = {'search_function': AniP.getAnimeURL,
              'result': None}
        adb = {'search_function': AniDB.getAnimeURL,
               'result': None}

        try:
            sqlCur.execute(
                'SELECT dbLinks FROM synonyms WHERE type = "Anime" AND lower(name) = ?',
                [searchText.lower()])
        except sqlite3.Error as e:
            print(e)

        alternateLinks = sqlCur.fetchone()

        if (alternateLinks):
            synonym = json.loads(alternateLinks[0])

            if synonym:
                malsyn = None
                if 'mal' in synonym and synonym['mal']:
                    malsyn = synonym['mal']
                anisyn = None
                if 'ani' in synonym and synonym['ani']:
                    anisyn = synonym['ani']

                apsyn = None
                if 'ap' in synonym and synonym['ap']:
                    apsyn = synonym['ap']

                adbsyn = None
                if 'adb' in synonym and synonym['adb']:
                    adbsyn = synonym['adb']

                mal['result'] = await roboragi.MAL as MAL.getAnimeDetails(
                    malsyn[0], malsyn[1]) if malsyn else None
                ani['result'] = await Anilist.getAnimeDetailsById(
                    anisyn) if anisyn else None
                ap['result'] = AniP.getAnimeURLById(apsyn) if apsyn else None
                adb['result'] = AniDB.getAnimeURLById(
                    adbsyn) if adbsyn else None
                print(ani['result'])

        else:
            data_sources = [ani, mal]
            aux_sources = [ap, adb]
            # aux_sources = [ap]

            synonyms = set([searchText])

            for x in range(len(data_sources)):
                for source in data_sources:
                    if source['result']:
                        break
                    else:
                        for synonym in synonyms:
                            if synonym in source['checked_synonyms']:
                                continue

                            source['result'] = await source['search_function'](
                                synonym)
                            source['checked_synonyms'].append(synonym)

                            if source['result']:
                                break

                    if source['result']:
                        synonyms.update([synonym.lower() for synonym in
                                         source['synonym_function'](
                                             source['result'])])

            for source in aux_sources:
                for synonym in synonyms:
                    source['result'] = await source['search_function'](synonym)

                    if source['result']:
                        break

        if ani['result'] or mal['result']:
            try:
                titleToAdd = ''
                if mal['result']:
                    if 'title' in mal['result']:
                        titleToAdd = mal['result']['title']
                '''if hb['result']:
                    if 'title' in hb['result']:
                        titleToAdd = hb['result']['title']'''
                if ani['result']:
                    if 'title_romaji' in ani['result']:
                        titleToAdd = ani['result']['title_romaji']

                if not blockTracking:
                    DatabaseHandler.addRequest(titleToAdd, 'Anime',
                                               message.author.id,
                                               message.server.id)
            except:
                traceback.print_exc()
                pass
        if mal['result']:
            print('trying to add an anime to cache')
            try:
                DatabaseHandler.addMalEntry('malanime', mal['result'])
            except:
                traceback.print_exc()
                pass
        if ani:
            try:
                DatabaseHandler.addAniEntry('anilistanime', ani['result'])
            except:
                traceback.print_exc()
                pass
        if not canEmbed:
            return CommentBuilder.buildAnimeComment(isExpanded, mal['result'],
                                                    ani['result'],
                                                    ap['result'],
                                                    adb['result'])
        else:
            return CommentBuilder.buildAnimeEmbed(isExpanded, mal['result'],
                                                  ani['result'], ap['result'],
                                                  adb['result'])

    except Exception as e:
        traceback.print_exc()
        return None


# Builds an LN reply from multiple sources
async def buildLightNovelReply(searchText, isExpanded, message, canEmbed,
                               blockTracking=False):
    try:
        mal = {'search_function': roboragi.MAL as MAL.getLightNovelDetails,
                                                  'synonym_function': roboragi.MAL as MAL.getSynonyms,
                                                                                      'checked_synonyms': [],
        'result': None}
        ani = {'search_function': Anilist.getLightNovelDetails,
               'synonym_function': Anilist.getSynonyms,
               'checked_synonyms': [],
               'result': None}
        nu = {'search_function': NU.getLightNovelURL,
              'result': None}
        lndb = {'search_function': LNDB.getLightNovelURL,
                'result': None}

        try:
            sqlCur.execute(
                'SELECT dbLinks FROM synonyms WHERE type = "LN" AND lower(name) = ?',
                [searchText.lower()])
        except sqlite3.Error as e:
            print(e)

        alternateLinks = sqlCur.fetchone()

        if (alternateLinks):
            synonym = json.loads(alternateLinks[0])

            if synonym:
                malsyn = None
                if 'mal' in synonym and synonym['mal']:
                    malsyn = synonym['mal']

                anisyn = None
                if 'ani' in synonym and synonym['ani']:
                    anisyn = synonym['ani']

                nusyn = None
                if 'nu' in synonym and synonym['nu']:
                    nusyn = synonym['nu']

                lndbsyn = None
                if 'lndb' in synonym and synonym['lndb']:
                    lndbsyn = synonym['lndb']

                mal['result'] = await roboragi.MAL as MAL.getLightNovelDetails(
                    malsyn[0], malsyn[1]) if malsyn else None
                ani['result'] = await Anilist.getMangaDetailsById(
                    anisyn) if anisyn else None
                nu['result'] = NU.getLightNovelById(nusyn) if nusyn else None
                lndb['result'] = LNDB.getLightNovelById(
                    lndbsyn) if lndbsyn else None

        else:
            data_sources = [ani, mal]
            aux_sources = [nu, lndb]

            synonyms = set([searchText])

            for x in range(len(data_sources)):
                for source in data_sources:
                    if source['result']:
                        break
                    else:
                        for synonym in synonyms:
                            if synonym in source['checked_synonyms']:
                                continue

                            source['result'] = await source['search_function'](
                                synonym)
                            source['checked_synonyms'].append(synonym)

                            if source['result']:
                                break

                    if source['result']:
                        synonyms.update([synonym.lower() for synonym in
                                         source['synonym_function'](
                                             source['result'])])

            for source in aux_sources:
                for synonym in synonyms:
                    source['result'] = await source['search_function'](synonym)

                    if source['result']:
                        break

        if ani['result'] or mal['result']:
            try:
                titleToAdd = ''
                if mal['result']:
                    titleToAdd = mal['result']['title']
                if ani['result']:
                    try:
                        titleToAdd = ani['result']['title_romaji']
                    except:
                        titleToAdd = ani['result']['title_english']

                if (str(message.server).lower is not 'nihilate') and (str(
                        message.server).lower is not 'roboragi') and not blockTracking:
                    DatabaseHandler.addRequest(titleToAdd, 'LN',
                                               message.author.id,
                                               message.server.id)
            except:
                traceback.print_exc()
                pass
        if mal['result']:
            try:
                DatabaseHandler.addMalEntry('malmanga', mal['result'])
            except:
                traceback.print_exc()
                pass
        if ani['result']:
            try:
                DatabaseHandler.addAniEntry('anilistmanga', ani['result'])
            except:
                traceback.print_exc()
                pass
        if not canEmbed:
            return CommentBuilder.buildLightNovelComment(isExpanded,
                                                         mal['result'],
                                                         ani['result'],
                                                         nu['result'],
                                                         lndb['result'])
        else:
            return CommentBuilder.buildLightNovelEmbed(isExpanded,
                                                       mal['result'],
                                                       ani['result'],
                                                       nu['result'],
                                                       lndb['result'])
    except Exception as e:
        traceback.print_exc()
        return None


# Checks if the bot is the parent of this comment.
def isBotAParent(comment, reddit):
    try:
        parentComment = reddit.get_info(thing_id=comment.parent_id)

        if (parentComment.author.name == USERNAME):
            return True
        else:
            return False

    except:
        # traceback.print_exc()
        return False
