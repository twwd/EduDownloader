#!/usr/bin/env python3
import argparse
import importlib
import os
import re
import sqlite3
from datetime import datetime
from urllib.parse import urljoin

import requests
import yaml


def load_plugin_class(plugin_class_str):
    """
    dynamically load a class from a string
    """
    class_data = plugin_class_str.split(".")
    module_path = "plugins." + ".".join(class_data[:-1])
    class_str = class_data[-1]

    mod = importlib.import_module(module_path)
    return getattr(mod, class_str)


# print if verbose output is on
def log(msg):
    if verbose_output:
        print(msg)


def course_loop():
    download_count = 0
    skip_count = 0

    # import config
    try:
        with open(os.path.join(os.path.dirname(__file__), 'data', 'config.yaml'), 'r', encoding='utf-8') as config_file:
            config = yaml.load(config_file)
    except FileNotFoundError:
        print("Please provide a config file under data/config.yaml.")
        return

    # make the initial request to get the token
    session = requests.Session()

    # Loop through sources
    for src_cfg in config:
        # check if there are courses to download from
        if 'courses' not in src_cfg or (source_part is not None and src_cfg['name'] not in source_part):
            continue

        log('\n\nSource: %s' % src_cfg['name'])

        # load dynamically the source class
        try:
            src_class = load_plugin_class(src_cfg['class'])
            src = src_class()
        except AttributeError:
            print('Class %s not found. Check your config file.' % src_cfg['class'])
            continue
        except ImportError:
            print(
                'Class %s not found. Check your config file' % src_cfg['class']
                + ' and ensure you have the class qualifier relative to the plugin directory.')
            continue

        # login
        if 'login_url' in src_cfg and 'username' in src_cfg and 'password' in src_cfg:
            src.login(session, src_cfg['login_url'], src_cfg['username'], src_cfg['password'])

        # loop through courses
        for course in src_cfg['courses']:

            # check if only some courses should be checked
            if course_part is not None and course['name'] not in course_part:
                continue

            log('\nCourse: %s\n' % course['name'])

            if 'path' in course and course['path'] is not None:
                course_url = urljoin(src_cfg['base_url'], course['path'])
            elif 'param' in course and course['param'] is not None:
                course_url = src.course_url(src_cfg['base_url'], course['param'])
            else:
                course_url = src_cfg['base_url']

            # regex pattern for link text and file name
            text_pattern = re.compile(course['pattern'])

            filename_pattern = None
            if 'filename_pattern' in course:
                filename_pattern = re.compile(course['filename_pattern'])

            # get all relevant links from the source site
            links = src.link_list(session, course_url)

            if links is None:
                continue

            for link in links:
                if text_pattern.search(link[0]) is not None:
                    # request file http header
                    file_request = session.head(link[1], allow_redirects=True)

                    # get file name
                    if 'Content-Disposition' in file_request.headers:
                        file_disposition = file_request.headers['Content-Disposition']
                        file_name = file_disposition[
                                    file_disposition.index('filename=') + 10:len(file_disposition) - 1].encode(
                            'latin-1').decode('utf8')
                    else:
                        # last part of the link (usually filename)
                        file_name = link[1].rsplit('/', 1)[-1]

                    # check extension
                    file_ext = os.path.splitext(file_name)[1]
                    if 'ext' in course and course['ext'] is not False:
                        if file_ext != course['ext'] or file_ext not in course['ext']:
                            continue

                    # check file name
                    if filename_pattern is not None and filename_pattern.search(file_name) is None:
                        continue

                    # get last modified date as timestamp
                    if 'Last-Modified' in file_request.headers:
                        file_last_modified = int(datetime.strptime(file_request.headers['Last-Modified'], '%a, %d %b %Y %H:%M:%S %Z').timestamp())
                    else:
                        print("No timestamp found for file %s" % file_name)
                        continue

                    # adjust file name
                    if 'rename' in course and course['rename'] is not False:
                        # find a number
                        num = re.search('\d{1,3}', link[0])
                        if num is None:
                            num = re.search('\d{1,3}', file_name)
                        if num is None:
                            num = file_last_modified
                        else:
                            num = num.group(0)
                        file_name = course['rename'].replace('%', str(num)) + file_ext

                    # remove trailing whitespaces
                    file_name = file_name.strip()

                    # the complete file path
                    file_path = os.path.join(course['local_folder'], file_name)

                    # fetch old timestamp from database
                    file_last_modified_old = c.execute(
                        'SELECT last_modified FROM file_modifications WHERE source=? AND course=? AND file_name=?',
                        (src_cfg['name'], course['name'], file_name)).fetchone()

                    # save file and timestamp in the database if it doesn't exists
                    if not simulate and file_last_modified_old is None:
                        c.execute(
                            '''
                            INSERT INTO file_modifications (source, course, file_name, file_path, last_modified)
                            VALUES (?,?,?,?,?)
                            ''',
                            (src_cfg['name'], course['name'], file_name, file_path, file_last_modified))
                    # update timestamp if there's a newer version of the file
                    elif not simulate and file_last_modified > file_last_modified_old[0]:
                        c.execute(
                            'UPDATE file_modifications SET last_modified=? WHERE source=? AND course=? AND file_name=?',
                            (file_last_modified, src_cfg['name'], course['name'], file_name))
                    # otherwise skip saving
                    else:
                        skip_count += 1
                        # log(file_name + ' (skipped)')
                        continue

                    log(file_name + ' (new)')

                    if simulate:
                        conn.rollback()
                        continue

                    # request whole file
                    file_request = session.get(link[1])

                    # write file
                    try:
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, 'wb') as f:
                            f.write(file_request.content)
                            download_count += 1
                    except FileNotFoundError:
                        print('Can\'t write file to %s' % file_path)
                        conn.rollback()

                    # save changes to the database
                    conn.commit()

    # display count of downloaded files
    log('\nDownloaded %i file(s), skipped %i file(s)' % (download_count, skip_count))


def clear_course():
    if course_to_clear[0] == 'all':
        c.execute("DELETE FROM file_modifications")
        log('\nCleared all courses')
    else:
        c.execute("DELETE FROM file_modifications WHERE course=?", course_to_clear)
        log('\nCleared course %s' % course_to_clear[0])
    conn.commit()


# command line args
parser = argparse.ArgumentParser(
    description='A simple script for downloading slides and exercises for university lectures.')
parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
parser.add_argument('-c', '--course', action='append', help='specify a course which should be checked')
parser.add_argument('-s', '--source', action='append', help='specify a source which should be checked')
parser.add_argument('-sim', '--simulate', action='store_true', help='specify if the process should only be simulated')
parser.add_argument('--clear', action='append',
                    help='specify a course which files should be deleted from the database (not from file system).'
                         + 'Use keyword \'all\' to clear the whole database')
args = parser.parse_args()

verbose_output = args.verbose
simulate = args.simulate
course_part = args.course
source_part = args.source
course_to_clear = args.clear

# database for timestamps
conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), 'data', 'file_modifications.db'))
c = conn.cursor()

# check if table exists otherwise create it
c.execute(
    '''
    CREATE TABLE IF NOT EXISTS file_modifications (
        id	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        course	TEXT,
        file_name	TEXT,
        file_path TEXT,
        last_modified	INTEGER
    );
    ''')

if simulate:
    log("Simulation on")

if course_to_clear is not None:
    clear_course()
else:
    course_loop()

# close cursor
c.close()
