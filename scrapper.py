import requests
from bs4 import BeautifulSoup
from subprocess import call
import subprocess
import os
from functools import partial
from multiprocessing import Pool
import urllib.request

class Scrapper:
    """Scrapper use extractors and actors against web pages.
    
    The Scrapper is an iterator that can be run recursively on a list of pages.
    After having downloaded the informations, a special extractor is used to 
    get the next url if any. 

    Note:
        If you only want to get the information from one page, you may want to use
        the `extract` helper function instead.

        The extractors given can be either a css selector or a function.
        You can get the selector with Chrome > Inspect > Right Click
        on the HTML element in the sidebar showing up > Copy > Copy selector

    Args:
        url (str): An url the scrapper will start with

        next_url_extractor (func, optional): A function getting a soup argument and
            returning the next url to scrap.

        extractors (list of func, optional): Functions that will be run against the 
            webpage in order to get informations. Get a soup argument and return an
            object or None. *It must be returning a Str* if used by a default actor

            Example:
                def get_video(soup):
                    video_url = soup.find(id='wistiaVideo')
                    return video_url and video_url['src']
        
        actors (list of object, optional): the actors are `D_object` inherited objects
            that must contains the methods `feed(self, str)` and `consume(self)`. It is
            usually aggregating the informations of a whole pagination and act on these.

        cookies (dict, optional): These are used in the HTTP requests, can be used to
            authenticate the user.

        pagination (int, optional): The scrapper run against the `pagination` next pages
            at each iteration.

    """

    def __init__(self, url=None, next_url_extractor=None, extractors=[], actors=[], cookies={}, pagination=10, verbose=False):
        self.url = url
        self.next_url_extractor = next_url_extractor
        self.extractors = list(map(self.format_extractor, extractors))
        self.actors = actors
        self.cookies = cookies
        self.pagination = pagination
        self.verbose = verbose

    def __iter__(self):
        return self

    def __next__(self):
        if not self.url:
            raise StopIteration

        result = []
        for _ in range(self.pagination):
            if self.url:
                infos, actors, self.url = self._page()
                result.append(infos)
        
        for actor in actors:
            actor.consume()

        return result

    def _page(self, url=None):
        url = url or self.url

        if self.verbose:
            print('[scrapper]', url)
        
        page = requests.get(url, cookies=self.cookies)
        soup = BeautifulSoup(page.content, 'html.parser')
        infos = [extractor(soup) for extractor in self.extractors]
        infos =  list(filter(None.__ne__, infos))
        actors = [actor.feed(soup) for actor in self.actors]

        next_url = self.next_url_extractor and self.next_url_extractor(soup)
        return infos, actors, next_url

    def page(self, url=None):
        infos, actors, next_url = self._page(url)
        for actor in actors:
            actor.consume()

        return infos, actors, next_url

    def run(self):
        return [i for i in self]

    @staticmethod
    def format_extractor(extractor):
        if isinstance(extractor, str):
            extractor = extractor.replace('nth-child', 'nth-of-type')
            func_extractor = lambda soup: soup.select(extractor)
        else:
            func_extractor = extractor
        
        return func_extractor

def extract(url, extractors, *args, **kwargs):
    """Helper function which return the extractors result form one page.
    
    Note:
        The extractors given can be either a css selector or a function.
        You can get the selector with Chrome > Inspect > Right Click
        on the HTML element in the sidebar showing up > Copy > Copy selector
    
    Args:
        url (str): The url of the web page to get
        
        extractors (list of str or list of func or str or func): Can get a
        css selector or a function with a the html BeautifulSoup Tag. It can
        also be a list of several of both.
        
        *args (list): Miscellaneous arguments given to `Scrapper` 

        **kwargs (dict): Miscellaneous named arguments given to `Scrapper` 
    """
    if isinstance(extractors, list):
        s = Scrapper(url, extractors=extractors, *args, **kwargs)
        return s.page()[0]
    else:
        s = Scrapper(url, extractors=[extractors], *args, **kwargs)
        return s.page()[0][0]

class Object_DL:
    def _type(self):
        class_name = self.__class__.__name__

        return class_name.split('_')[0]

    def __init__(self, extractor, path=None, name=None, *args, **kwargs):
        self.extractor = extractor
        self.name = name or self._type()
        self.path = path or self.name.lower() + 's'
        self.urls = []
        os.makedirs(self.path, exist_ok=True)

    @staticmethod
    def purge_locals(local):
        del local['self']
        local.update(local.pop('kwargs'))
        return local

    def feed(self, soup):
        self.urls.append(self.extractor(soup))
        return self

    def _consume(self, n_url, args):
        i, url = args
        length_n = len(n_url)
        template_msg = '[downloader] {0} [{1:0{3}}/{2}] '.format(self.name, i+1, n_url, length_n)
        print(template_msg + 'consume ' + url)
        
        try:
            self.download(url)
        except Exception as e:
            print(template_msg + 'ERROR:\n{0}'.format(str(e)))
        else:
            print(template_msg + 'Done')
    
    def consume(self):
        urls = list(filter(None.__ne__, self.urls))
        func = partial(self._consume, str(len(urls)))

        with Pool(10) as p:
            p.map(func, enumerate(urls))

        self.urls = []

    def download(self, url):
        raise ValueError('`download` method must be overridden')


class Youtube_DL (Object_DL):
    class YtDlLogger(object):
        def debug(self, msg):
            pass

        def warning(self, msg):
            pass

        def error(self, msg):
            pass

    def __init__(self, ydl_opts=None, *args, **kwargs):
        super().__init__(**self.purge_locals(locals()))
        self.ydl_opts = ydl_opts or {}

        if 'logger' not in self.ydl_opts:
            self.ydl_opts['logger'] = self.YtDlLogger()

        if 'format' not in self.ydl_opts:
            self.ydl_opts['format'] = 'bestaudio/best'

        if 'outtmpl' not in self.ydl_opts:
            self.ydl_opts['outtmpl'] = os.path.join(self.path, '%(title)s.%(ext)s')

    def consume(self):
        urls = list(filter(None.__ne__, self.urls))
        print('[batch_downloader] {0} {1} objects consumed.'.format(self.name, len(urls)))

        try:
            with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
                ydl.download(urls)
        except Exception as e:
            print('[batch_downloader] {0} ERROR:\n{1}'.format(self.name, str(e)))
        else:
            print('[batch_downloader] {0} Done'.format(self.name))

        self.urls = []

class File_DL (Object_DL):
    def __init__(self, extractor, *args, **kwargs):
        super().__init__(**self.purge_locals(locals()))

    def download(self, url):
        name = os.path.basename(url)
        urllib.request.urlretrieve(url, os.path.join(self.path, name))  
