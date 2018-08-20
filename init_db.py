from scrapper import extract
import re
import string
import argparse
import re
import sys
from subprocess import Popen, PIPE
import os
import glob

from subhd.main import SubHDApp
from subhd.subtitle import *
from subhd.search import SubHDSearch

from compare import RAW_SUBTITLES_PATH, crush_subtitles

from subprocess import STDOUT, check_output
import subprocess

def sanatize_movie_name(movie_name):
    return movie_name.replace('\n', '').replace('\t', '').replace('\r', '').strip()

def get_movies_from_index(index):
    if index != 'AZ':
        index = 'AZ/' + index
    r = extract('http://chinesemov.com/{}.html'.format(index), 'ul')
    movie_list = r[1]
    return [(movie.get('href'), sanatize_movie_name(movie.get_text())) for movie in movie_list.find_all('a')]

def get_movies():
    print('> Get movie names')
    list_index = list(string.ascii_uppercase) + ['AZ']
    movies = []

    for index in list_index:
        movies += get_movies_from_index(index)

    return movies

class FixSubHDSearch(SubHDSearch):
    def select_subtitle(self, *, choice):
        entries = list(self.entries())
        id_entry = entries[choice - 1].path.split('/')[2]
        return FixSubHDSubtitle(id=id_entry)

class FixSubHDSubtitle(SubHDSubtitle):
    def __init__(self, id):
        super(FixSubHDSubtitle, self).__init__(id)
        self.archive_name = None

    def get_file_url(self):
        response = requests.post(AJAX_ENDPOINT, data={"sub_id": self.id})
        url = response.json().get("url")
        if url == "http://dl.subhd.com":
            raise SubHDDownloadException()
        else:
            self.archive_type = url.split(".")[-1].lower()
            self.archive_name = url.split("/")[-1]
            return url

    def download_archive(self):
        response = requests.get(self.get_file_url())

        with open(self.archive_name, 'wb') as archive:
            for chunk in response.iter_content(CHUNK_SIZE):
                archive.write(chunk)

    def extract_subtitles(self):
        self.download_archive()
        cmds = []

        if self.archive_type == 'rar':
            cmds = ['unrar', 'x']
        elif self.archive_type == 'zip':
            cmds = ['unzip']
        elif self.archive_type == '7z':
            cmds = ['7zr', 'e']
        else:
            message = "Archive type {0} is not yet " \
                      "supported".format(self.archive_type)
            raise SubHDDecompressException(message)

        cmds.append('../' + self.archive_name)
        try:
            check_output(cmds, stderr=STDOUT, timeout=5)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            os.chdir('..')
            os.remove(self.archive_name)
            return False

        os.remove(self.archive_name)
        return True 

    def move_subtitles(self, filename):
        if self.extract_subtitles():
            files = (glob.glob(os.path.join('tmp', '*', '*.简体.srt')) + glob.glob(os.path.join('tmp', '*.简体.srt')) +
                glob.glob(os.path.join('tmp', '*', '*chs.srt')) + glob.glob(os.path.join('tmp', '*chs.srt')) + 
                glob.glob(os.path.join('tmp', '*', '*zh.srt')) + glob.glob(os.path.join('tmp', '*zh.srt')))
            
            if files:
                try:
                    os.rename(files[0], os.path.join(RAW_SUBTITLES_PATH, filename + '.srt'))
                except:
                    pass
            else:
                files = glob.glob(os.path.join('tmp', '*', '*.srt')) + glob.glob(os.path.join('tmp', '*.srt'))
                if files:
                    try:
                        os.rename(files[0], os.path.join(RAW_SUBTITLES_PATH, filename + '.srt'))
                    except:
                        pass

            files = glob.glob(os.path.join('tmp', '*', '*')) + glob.glob(os.path.join('tmp', '*'))
            for f in files:
                try:
                    pass
                    os.remove(f)
                except:
                    pass

class FixSubHDApp(SubHDApp):
    def __init__(self, filename):
        self.filename = filename
        self.search = None

    def exist_subtitle(self):
        try:
            self.search = FixSubHDSearch(keyword=self.filename)
            return len(list(self.search.entries())) > 0
        except:
            pass

        return False

    def main(self):
        if self.exist_subtitle():
            print('Found: {}'.format(self.filename))
            subtitle = self.search.select_subtitle(choice=1)
            subtitle.move_subtitles(self.filename)
        else:
            print('Skip:  {}'.format(self.filename))

if __name__ == "__main__":
    movies = get_movies()[1681+254+92+679+56+6:]
    n = len(movies)
    n_length = len(str(n))

    print('> Download subtitles')
    for i, (_, movie_name) in enumerate(movies):
        print('[{0:{2}}/{1}] '.format(i, n, n_length), end='', flush=True)
        app = FixSubHDApp(movie_name)
        app.main()

    crush_subtitles()
