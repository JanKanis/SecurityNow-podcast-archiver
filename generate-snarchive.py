#!/usr/bin/env python3
# license: GPLv3 or later

"""
Usage: 
- run this script
- put the generated snarchive.xml file in a public Dropbox/Google Drive/other cloud drive folder
- point your podcast player at the link of the file

To generate a longer archive, add the urls of the older archive pages to the 'urls' list below.
"""

backto = 2005
#urls = ['https://www.grc.com/securitynow.html', 'https://www.grc.com/sn/past/2014', 'https://www.grc.com/sn/past/2013', 'https://www.grc.com/sn/past/2012']

output = 'snarchive.xml'


import tzlocal, datetime
import string
import requests, bs4
from xml.sax.saxutils import escape as esc


now = datetime.datetime.now(tzlocal.get_localzone())
nowfmt = now.strftime("%a, %d %b %Y %H:%M:%S %z")

thisyear = now.year
urls = ['https://www.grc.com/securitynow.htm']
if backto:
  urls += ('https://www.grc.com/sn/past/{}.htm'.format(year) for year in range(thisyear-1, backto-1, -1))

template = string.Template(open('sn-template.xml').read())
itemtemplate = string.Template(open('sn-item.xml').read())


def download_page(url):
  print("\ndownloading {}...".format(url))
  r = requests.get(url)
  if not r.ok:
    raise Exception("failed to download {}: {} {}".format(url, r.status_code, r.reason))
  return r.content


def find_episodes(links):
  for l in links:
    try:
      page = download_page(l)
      soup = bs4.BeautifulSoup(page, 'html.parser')
      yield from find_episodes_in_page(soup)
    except Exception as e:
      print(e)


def find_episodes_in_page(soup):
  links = soup.find_all('a')
  
  for link in links:
    try:
      episode_nr = int(link.attrs['name'])
      yield get_item(soup, episode_nr)
    except Exception:
      pass


def get_item(soup, item):
  link = soup.find('a', attrs={'name':str(item)})
  
  header = link.findNext('table')
  episode, date, length = (x.strip() for x in header.text.split('|'))
  nr = int(episode.partition('#')[2])
  minutes = int(length.split(' ')[0])
  
  body = header.findNext('table')

  title = body.findChild('font', size=2).text
  description = body.findChild('font', size=1).text
  if description.startswith(title):
    description = description.partition(title)[2]
  description = description.strip()
  title = title.strip()
  assert description

  return dict(episode=episode,
              date=date,
              length=length,
              minutes=minutes,
              nr=nr,
              title=title,
              description=description)


def item_rss(links):
  for episode in find_episodes(links):
    minutes = episode['minutes']
    duration = "{}:{}:00".format(minutes//60, minutes%60)
    yield episode['nr'], itemtemplate.substitute(
      NR=esc(str(episode['nr'])),
      NR4=esc(str(episode['nr']).rjust(4, '0')),
      DATE=esc(episode['date']),
      DURATION=esc(duration),
      TITLE=esc(episode['title']),
      DESCRIPTION=esc(episode['description']))



def generate_rss(links):
  header = True
  episodes = []
  for nr, episode_rss in item_rss(links):
    if header: 
      print("Found episodes: ", end='', flush=True)
      header = False
    print(nr, end=', ', flush=True)
    episodes.append(episode_rss)

  if episodes:
    out = open(output, 'w')
    out.write(template.substitute(NOW=nowfmt, ITEMS=''.join(episodes)))
  else:
    print("\nError: No episodes found!")


generate_rss(urls)
