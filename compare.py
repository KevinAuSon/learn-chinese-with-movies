import os
import glob
import json
import io
import shutil
import re
from os import path
from subprocess import Popen, PIPE

import pysrt

from known_car import get_user_words

CRUSHED_SUBTITLES_PATH   = path.join('data', 'crushed-subtitles')
SEGMENTED_SUBTITLES_PATH = path.join('data', 'segmented-subtitles')
RAW_SUBTITLES_PATH       = path.join('data', 'subtitles')

def clean(path_file, files_re='*'):
    files = glob.glob(path.join(path_file, files_re))
    for f in files:
        if path.isfile(f):
            os.remove(f)
        else:
            shutil.rmtree(f)

def convert_to_utf8(subtitle, current='gbk'):
    subs = None
    with open(subtitle, 'rb') as in_f:
        subs = [line.decode("gbk") for line in in_f.readlines()]

    with open(subtitle, 'w', encoding='utf8') as out_f:
        for sub in subs:
            out_f.write(sub)

def sanitize_name(filename):
    path_file, name = path.split(filename)
    name = re.sub(r'[^0-9a-zA-Z _\.]+', '', name)
    return path.join(path_file, name.replace(' ', '_'))

def extract_subtitles(filename_re='*.srt'):
    print('> Convert subtitles to text files')
    subtitles = glob.glob(path.join(RAW_SUBTITLES_PATH, filename_re))

    for subtitle in subtitles:
        try:
            subs = pysrt.open(subtitle)
        except UnicodeDecodeError:
            try:
                convert_to_utf8(subtitle)
            except UnicodeDecodeError:
                try:
                    convert_to_utf8(subtitle, "big5")
                except UnicodeDecodeError:
                    continue
            subs = pysrt.open(subtitle)

        file_name = sanitize_name(path.join('tmp', path.split(subtitle)[1]))

        with open(file_name, 'w') as out_f:
            for sub in subs:
                out_f.write(sub.text + '\n')

def list_to_dict(words):
    result = {}
    for sentence in words:
        for word in sentence.split(" "):
            word_count = result.get(word, 0)
            result[word] = word_count + 1

    return result

def segment_subtitles(filename_re='*.srt'):
    files = glob.glob('../tmp/{}'.format(filename_re))
    print('> Segment {} files'.format(len(files)))
    
    process = Popen(['./segment.sh', ','.join(files)], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    segmented_text = stdout.decode('UTF-8').split('\n')

    for file in files:
        len_file = 0
        with open(file, 'r') as in_f:
            len_file = len(in_f.readlines())
        
        word_list = segmented_text[:len_file]
        crushed_file_name   = path.join('..', CRUSHED_SUBTITLES_PATH, path.split(file)[1])
        segmented_file_name = path.join('..', SEGMENTED_SUBTITLES_PATH, path.split(file)[1])
        
        with io.open(segmented_file_name, 'w', encoding='utf8') as segmented_file:
            for line in word_list:
                segmented_file.write(line + '\n')

        with io.open(crushed_file_name, 'w', encoding='utf8') as json_file:
            json.dump(list_to_dict(word_list), json_file, ensure_ascii=False)
            segmented_text = segmented_text[len_file:]
    
    # assert len(segmented_text) == 0
    
def crush_subtitles():
    # clean(CRUSHED_SUBTITLES_PATH)
    # clean(SEGMENTED_SUBTITLES_PATH)
    clean('tmp')
    extract_subtitles()
    segment_subtitles()
    clean('tmp')

def get_compatibility_subtitle(user_words, filename, nb_new=10):
    similar_u_count = 0
    similar_count = 0
    all_count = 0
    all_u_count = 0
    not_known = {}

    with open(filename, 'r') as in_f:
        chars = json.load(in_f)
        all_u_count = len(chars)
        for char, nb in chars.items():
            all_count += nb
            if char in user_words:
                similar_u_count += 1
                similar_count += nb
            else:
                not_known[char] = nb
    
    not_known = sorted(not_known.items(), key=lambda x: x[1], reverse=True)


    file_name = path.split(filename)[1]
    file_name = file_name.split('.')[:-1]

    if all_count > 0:
        return {
              'name': '.'.join(file_name)
            , 'top_new_vocabulary': not_known[:nb_new]
            , 'all_count': all_count 
            , 'similar_count': similar_count
            , 'percentage_similar': int(similar_count/all_count * 100)
            , 'all_u_count': all_u_count
            , 'similar_u_count': similar_u_count
            , 'percentage_u_similar': int(similar_u_count/all_u_count * 100)
        }
    else:
        return None

def get_compatibilities_subtitles(user, path_re='*', n=-1):
    user_words = get_user_words(user)
    subtitles = glob.glob(path.join(CRUSHED_SUBTITLES_PATH, path_re))
    subtitles = [get_compatibility_subtitle(user_words, subtitle) for subtitle in subtitles]
    subtitles = [sub for sub in subtitles if sub]
    subtitles = sorted(subtitles, key = lambda x: x['percentage_similar'], reverse=True)
    subtitles = subtitles[:n] if n > 0 else subtitles

    for subtitle in subtitles:
        print('>  {}%:\t{}'.format(subtitle['percentage_similar'], subtitle['name']))
        print(subtitle['top_new_vocabulary'])

# def higligh_subtitle(subtitle_file, words):
#     subs = pysrt.open(subtitle_file)

#     for sub in subs:
#         for word in words:
#             if word in sub.text:
#                 print(sub.text.replace(word, '\033[0;31m{}\033[0m'.format(word)))
#                 sub.text = sub.text.replace(word, '<font color=#FF0000>{}</font>'.format(word))

#     subs.save(subtitle_file, encoding='utf-8')
        
# # higligh_subtitle('test/Brotherhood.of.Blades.I.srt', ['就'])

def get_examples(highlight_char, user, subtitle_name='*'):
    user_words = get_user_words(user)
    subtitles = glob.glob(path.join(SEGMENTED_SUBTITLES_PATH, subtitle_name))

    for subtitle in subtitles:
        subs = []
        try:
            with open(subtitle, 'r', encoding='utf8') as in_f:
                subs = in_f.readlines()
        except UnicodeDecodeError:
            print('{} is not in utf-8, we could not open it'.format(path.split(subtitle)[1]))
            continue

        for sub in subs:
            filtered_sub = ''
            sub = sub[:-1].split(' ')

            if highlight_char in sub:
                for char in sub:
                    if char == highlight_char:
                        filtered_sub += '\033[0;41m{}\033[0m'.format(char)
                    elif char in user_words:
                        filtered_sub += '\033[0;32m{}\033[0m'.format(char)
                    else:
                        filtered_sub += char

                    filtered_sub += ' '
                print(filtered_sub)

if __name__ == "__main__":
    # crush_subtitles()
    get_compatibilities_subtitles('rinku', path_re='Finding_Mr_Right_2013.srt')
    get_examples('啊', 'rinku', 'Finding_Mr_Right_2013.srt')


# http://www.singchinesesongs.com/sing.php?singid=350
