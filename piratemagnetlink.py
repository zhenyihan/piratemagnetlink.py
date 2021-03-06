#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
import urllib
import codecs
from pyquery import PyQuery as pq
from subprocess import Popen, PIPE
import math
import multiprocessing

def sigmoid(x):
    return 1 / (1 + math.exp(-x))

class attrdict(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self
        
def get_movie_page(movie_name):
    url = 'http://thepiratebay.se/search/%s/0/99/200' % urllib.quote(movie_name)
    
    curl = Popen(('curl', '-L', '--socks5-hostname', '127.0.0.1:1080', url) , shell=False, bufsize=0, stdin=PIPE, 
    stdout=PIPE, stderr=PIPE, close_fds=True )
    
    content = curl.stdout.read()
    if curl.wait() == 0:
        return content
    return None

def calculate_score(item):
    score = - (10 - item.size) ** 2  + 144 * sigmoid(item.seeders * 0.04)
    if item.size < 3:
        score += (item.size - 3) * 10
    if item.size > 25:
        score -= (item.size - 20) * 10
    if item.seeders < 1:
        score -= 100
    title_lower = item.title.lower()
    for k,v in {
        '720p': 2,
        '1080p': 5,
        'bd': 5,
        'bluray': 5,
        'trilogy':10,
        'cam': -100,
        'dvd': -30,
        'iso': -30,
        'rus': -30,
    }.iteritems():
        if title_lower.find(k) >= 0:
            score += v
    return score
    
def parse(content):
    doc = pq(content)
    rows = doc.find('#searchResult tr')
    items = []
    for row in rows:
        row = pq(row)
        title_a = row.find('.detLink')
        if not title_a:
            print 'no title_a'
            continue
        title = title_a.text()
        link = title_a.attr('href')
        magnet_a = row.find('a[title*=\'magnet\']')
        magnet = magnet_a.attr('href')
        seeders = row.find('td')[2].text
        font_desc = row.find('font.detDesc')
        size = font_desc.text().split(',')[1].strip()
        is_mb = False

        size_frag = filter(lambda a:a, re.split('\s|\xa0', size))
        if size_frag[2] != 'GiB':
            if size_frag[2] == 'MiB':
                is_mb = True
            else:
                print 'no size'
                continue
        
        item = attrdict()
        item.title = codecs.encode(title, 'utf-8')
        item.magnet = magnet 
        # item.link = link 
        item.seeders = int(seeders) 
        item.size = float(size_frag[1]) 
        if is_mb:
            item.size = item.size / 1024
        item.score = float(calculate_score(item))
        items.append(item)
    else:
        print 'no rows'
        
    items.sort(key=lambda x:x.score, reverse=True)
    return items
   
    
if __name__ == '__main__':
    with open('output.txt', 'wb') as o:
        f = open('favo.txt', 'rb')
        def process(line):
            words = line.strip().split('\t')
            print line
            title, year = line.rsplit('(', 1)
            year = year.split(')')[0].strip()
            items = parse(get_movie_page(line))
            if not items:
                print 'cant find %s, trying %s instead' % (line, title)
                items = parse(get_movie_page(title))
            for item in items:
                print item
            if not items:
                print 'cant find %s' % title
            if len(items) > 0:
                item = items[0]
                print >> o, '%s\t%s\t%s\t%f\t%f' % (line, item.title, item.magnet, item.size, item.seeders)
                o.flush()
            else:
                print >> o, '%s\t\t\t\t' % line
        p = multiprocessing.Pool(5)
        p.map(process, f)
