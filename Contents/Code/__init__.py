# -*- coding: utf-8 -*-
# @movies
import re

ATMOVIES_SEARCH = 'http://search.atmovies.com.tw/search/'
ATMOVIES_DETAIL = 'http://app2.atmovies.com.tw/film/%s/'

####################################################################################################
def Start():
  HTTP.CacheTime = CACHE_1DAY
  HTTP.Headers['Accept'] = 'text/html'

def LevenshteinRatio(first, second):
  return 1 - (Util.LevenshteinDistance(first, second) / float(max(len(first), len(second))))

####################################################################################################
class AtMoviesAgent(Agent.Movies):

  name = u'開眼電影網'
  languages = [Locale.Language.Chinese]
  primary_provider = False
  contributes_to = [
    'com.plexapp.agents.imdb',
    'com.plexapp.agents.themoviedb'
  ]

  def search(self, results, media, lang, manual):
    media_name = media.name
    media_year = media.year
    if media.primary_metadata is not None:
      media_name = media.primary_metadata.title
      media_year = media.primary_metadata.year
    Log.Debug('Search: %s (%s)' % (media_name, media_year))

    html = HTML.ElementFromURL(url=ATMOVIES_SEARCH,
                               headers={'Referer': ATMOVIES_SEARCH,
                                        'Content-Type': 'application/x-www-form-urlencoded'},
                               values={'fr': 'search-page',
                                       'enc': 'UTF-8',
                                       'type': 'F',
                                       'search_term': media_name,
                                       'x': '0',
                                       'y': '0'})

    for candidate in html.xpath('//header'):
      links = candidate.xpath('a[starts-with(@href,"/F/")]')
      if not links:
        continue
      id = links[0].get('href').strip('/').split('/')[-1]
      title = String.DecodeHTMLEntities(String.StripTags(links[0].text)).strip()
      year = candidate.xpath('font[@color="#606060"]')[0].text.strip()

      if media_year is None:
        score = 60
      elif int(year) == int(media_year):
        score = 100
      elif abs(int(year) - int(media_year)) == 1:
        # Sometimes Taiwan premiere date could be later
        score = 80
      else:
        score = 20

      en_title = ' '.join(map(lambda x: x.strip(), re.findall(u'[\u0000-\u00FF]+', title)))
      score = score * LevenshteinRatio(en_title, media_name)

      Log.Debug('Search: ID=%s, title=%s, year=%s, score=%d' % (id, title, year, score))
      results.Append(MetadataSearchResult(id=id, name=title, year=year, score=score, lang=lang))

  def update(self, metadata, media, lang):
    Log.Debug("Update: ID=%s" % metadata.id)
    doc = unicode(HTTP.Request(ATMOVIES_DETAIL % metadata.id))
    # html = HTML.ElementFromString(doc)

    title = re.search(u'<!-- filmTitle -->(.*)<!-- filmTitle end -->', doc, re.DOTALL).group(1)
    title = String.DecodeHTMLEntities(String.StripTags(title)).strip()
    metadata.title = title
    Log.Debug('Update: title=%s' % title)

    plot = re.search(u'劇情簡介(.*)<!-- Story info end -->', doc, re.DOTALL).group(1)
    plot = re.sub('[\r\n]+', ' ', plot)
    lines = re.split('<br\s*/?>', plot, flags=re.IGNORECASE)
    plot = '\n'.join(filter(None, map(lambda x: x.strip(), lines)))
    plot = String.DecodeHTMLEntities(String.StripTags(plot))
    metadata.summary = plot
