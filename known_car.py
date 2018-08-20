import os
import glob
import sys
from subprocess import Popen, PIPE
import string

def get_user_words(user):
    """Get a user words list"""
    path = os.path.join('users', user + '.txt')

    if os.path.isfile(path):
        with open(path, 'r') as in_f:
            chars = in_f.readlines()[0].replace('\n', '')
            if chars:
                return set(chars.split(','))

    return set()

def add_user_words(user, words):
    """Add words to a user list"""
    path = os.path.join('users', user + '.txt')
    words |= get_user_words(user)

    with open(path, 'w') as out_f:
       out_f.write(','.join(words))

def clean_file(path):
    """Remove the non-Chinese words from a file

    The function clean a file and write this new version
    in a new file. It will give as result the new path.
    """
    letters = list(string.ascii_lowercase)
    cleaned_words = []  

    with open(path, 'r') as in_f:
        words = ('').join(in_f.readlines()).split()
        for w in words:
            if not [l for l in letters if l in w]:
                cleaned_words.append(w)

    cleaned_file = os.path.join('tmp', path)
    with open(cleaned_file, 'w', encoding='utf8') as out_f:
        for w in cleaned_words:
            out_f.write(w + '\n')

    return cleaned_file

def segment_files(paths):
    """Segment a file into Chinese words

    This function takes in a bunch all the files fed and segment
    each line into a list of words. It uses the standford segmenter 
    which takes some time to initialize. It is then better when 
    given small files to give them all at once.
    """
    paths = paths if type(paths) is list else [paths]
    paths = ','.join([os.path.join('..', path) for path in paths])
    process = Popen(['./segment.sh', paths], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    segmented_text = stdout.decode('UTF-8').split('\n')
    
    return segmented_text

def add_file_to_user(user, path):
    """Add Chinese characters to a user profile
    
    The file is first purge from all the [a-z] characters in order
    to not take into account the translations or whatever other text
    is as well in the file. This function need to be made more
    robust tho.
    """
    path = clean_file(path)
    segmented = ' '.join(segment_files(path))
    segmented = set(segmented.replace(' ', ','))
    add_user_words(user, segmented)

if __name__ == "__main__":
    path = sys.argv[1]
    user = 'rinku'
    add_file_to_user(user, path)

    # add_user_words(user, words)
    # l = {'了','子','好','吗','白','勺','的','干','王','玉','水','氵','火','灬','汁','厂','厅','在','小','尔','他','她','日','月','明','宀','字','豕','家','文','辶','这','过','八','天','土','又','双','少','妙','尝','学','帅','巾','丑','豆','矢','短','口','叫','夕','名','千','舌','不','杯','七','艮','很','亿','万','几','亮','上','下','卡','门','们','可','哥','卜','仆','耳','取','最','斤','近','尸','匕','呢','己','见','觉','外','心','关','止','正','反','人','太','十','木','林','森','从','众','丛'}
