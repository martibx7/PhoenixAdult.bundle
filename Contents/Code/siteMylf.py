import PAsearchSites
import PAgenres
import PAactors
import PAutils
import re


def getJSONfromPage(url):
    data = PAutils.HTTPRequest(url)

    if data:
        jsonData = re.search(r'window\.__INITIAL_STATE__ = (.*);', data)
        if jsonData:
            return json.loads(jsonData.group(1))['content']
    return None


def search(results,encodedTitle,title,searchTitle,siteNum,lang,searchByDateActor,searchDate,searchSiteID):
    if searchSiteID != 9999:
        siteNum = searchSiteID

    directURL = searchTitle.replace(' ', '-').lower()
    if '/' not in directURL:
        directURL = directURL.replace('-', '/', 1)

    shootID = directURL.split('/', 2)[0]
    if not unicode(shootID, 'utf8').isdigit():
        shootID = None
        directURL = directURL.replace('/', '-', 1)
    else:
        directURL = directURL.split('/')[1]

    directURL = PAsearchSites.getSearchSearchURL(siteNum) + directURL
    searchResultsURLs = [directURL]

    if not searchResultsURLs:
        googleResults = PAutils.getFromGoogleSearch(searchTitle, siteNum)

        for sceneURL in googleResults:
            sceneURL = sceneURL.rsplit('?', 1)[0]
            if sceneURL not in searchResultsURLs:
                if ('/movies/' in sceneURL):
                    searchResultsURLs.append(sceneURL)

    for sceneURL in searchResultsURLs:
        detailsPageElements = getJSONfromPage(sceneURL)

        if detailsPageElements:
            contentName = None
            for name in ['moviesContent', 'videosContent']:
                if name in detailsPageElements:
                    contentName = name
                    break

            if contentName:
                detailsPageElements = detailsPageElements[contentName]
                curID = detailsPageElements.keys()[0]
                detailsPageElements = detailsPageElements[curID]
                titleNoFormatting = detailsPageElements['title']
                if 'mylfdom' in sceneURL:
                    subSite = 'MylfDom'
                else:
                    subSite = detailsPageElements['site']['name']

                if 'publishedDate' in detailsPageElements:
                    releaseDate = parse(detailsPageElements['publishedDate']).strftime('%Y-%m-%d')
                else:
                    releaseDate = parse(searchDate).strftime('%Y-%m-%d') if searchDate else ''
                displayDate = releaseDate if 'publishedDate' in detailsPageElements else ''

                if searchDate and displayDate:
                    score = 100 - Util.LevenshteinDistance(searchDate, releaseDate)
                else:
                    score = 100 - Util.LevenshteinDistance(searchTitle.lower(), titleNoFormatting.lower())

                results.Append(MetadataSearchResult(id='%s|%d|%s|%s' % (curID, siteNum, releaseDate, contentName), name='%s [Mylf/%s] %s' % (titleNoFormatting, subSite, displayDate), score=score, lang=lang))

    return results


def update(metadata,siteID,movieGenres,movieActors):
    metadata_id = str(metadata.id).split('|')
    sceneName = metadata_id[0]
    releaseDate = metadata_id[2]
    contentName = metadata_id[3]

    detailsPageElements = getJSONfromPage(PAsearchSites.getSearchSearchURL(siteID) + sceneName)[contentName][sceneName]

    # Studio
    metadata.studio = 'Mylf'

    # Title
    metadata.title = detailsPageElements['title']

    # Summary
    metadata.summary = detailsPageElements['description']

    # Tagline and Collection(s)
    metadata.collections.clear()
    if 'site' in detailsPageElements:
        subSite = detailsPageElements['site']['name']
    else:
        subSite = PAsearchSites.getSearchSiteName(siteID)
    metadata.tagline = subSite
    metadata.collections.add(subSite)

    # Release Date
    if releaseDate:
        date_object = parse(releaseDate)
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Actors
    movieActors.clearActors()
    actors = detailsPageElements['models']
    for actorLink in actors:
        actorID = actorLink['modelId']
        actorName = actorLink['modelName']
        actorPhotoURL = ''

        actorData = getJSONfromPage('%s/models/%s' % (PAsearchSites.getSearchBaseURL(siteID), actorID))
        if actorData:
            actorPhotoURL = actorData['modelsContent'][actorID]['img']

        movieActors.addActor(actorName, actorPhotoURL)

    # Genres
    movieGenres.clearGenres()
    genres = ["MILF", "Mature"]

    if subSite.lower() == "MylfBoss".lower():
        for genreName in ['Office', 'Boss']:
            movieGenres.addGenre(genreName)
    elif subSite.lower() == "MylfBlows".lower():
        for genreName in ['Blowjob']:
            movieGenres.addGenre(genreName)
    elif subSite.lower() == "Milfty".lower():
        for genreName in ['Cheating']:
            movieGenres.addGenre(genreName)
    elif subSite.lower() == "Mom Drips".lower():
        for genreName in ['Creampie']:
            movieGenres.addGenre(genreName)
    elif subSite.lower() == "Milf Body".lower():
        for genreName in ['Gym', 'Fitness']:
            movieGenres.addGenre(genreName)
    elif subSite.lower() == "Lone Milf".lower():
        for genreName in ['Solo']:
            movieGenres.addGenre(genreName)
    elif subSite.lower() == "Full Of JOI".lower():
        for genreName in ['JOI']:
            movieGenres.addGenre(genreName)
    elif subSite.lower() == "Mylfed".lower():
        for genreName in ['Lesbian', 'Girl on Girl', 'GG']:
            movieGenres.addGenre(genreName)
    elif subSite.lower() == "MylfDom".lower():
        for genreName in ['BDSM']:
            movieGenres.addGenre(genreName)
    if (len(actors) > 1) and subSite != "Mylfed":
        genres.append("Threesome")

    for genre in genres:
        movieGenres.addGenre(genre)

    # Posters
    art = [
        detailsPageElements['img']
    ]

    Log('Artwork found: %d' % len(art))
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'}
    for idx, posterUrl in enumerate(art, 1):
        if not PAsearchSites.posterAlreadyExists(posterUrl, metadata):
            # Download image file for analysis
            try:
                req = urllib.Request(posterUrl, headers=headers)
                img_file = urllib.urlopen(req)
                im = StringIO(img_file.read())
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if width > 1:
                    # Item is a poster
                    metadata.posters[posterUrl] = Proxy.Media(HTTP.Request(posterUrl, headers=headers).content, sort_order=idx)
                if width > 100 and width > height:
                    # Item is an art item
                    metadata.art[posterUrl] = Proxy.Media(HTTP.Request(posterUrl, headers=headers).content, sort_order=idx)
            except:
                pass

    return metadata
