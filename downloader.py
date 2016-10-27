#!/usr/bin/env python3
import argparse
import os
import re
import sqlite3
from datetime import datetime
from urllib.parse import urljoin

import requests
import yaml


# print if verbose output is on
def log(msg):
    if verbose_output:
        print(msg)


def course_loop():
    download_count = 0
    skip_count = 0

    # import config
    with open(os.path.join(os.path.dirname(__file__), 'data', 'config.yaml'), 'r', encoding='utf-8') as config_file:
        config = yaml.load(config_file)

    # load the sources module
    module = __import__('sources')

    # make the initial request to get the token
    session = requests.Session()

    # Loop through moodles
    for src in config:
        # check if there are courses to download from
        if 'courses' not in src or (source_part is not None and src['name'] not in source_part):
            continue

        log('\nSource: %s' % src['name'])

        # load dynamically the source class
        try:
            source_class = getattr(module, src['class'])
            source = source_class()
        except AttributeError:
            print('Class not found. Check your config file.')
            continue

        # login
        source.login(session, src['login_url'], src['username'], src['password'])

        # loop through courses
        for course in src['courses']:

            # check if only some courses should be checked
            if course_part is not None and course['name'] not in course_part:
                continue

            log('Course: %s' % course['name'])

            course_url = urljoin(src['base_url'], '/course/view.php?id=' + str(course['id']))

            # regex pattern
            pattern = re.compile(course['pattern'])

            # get all relevant links from the source site
            links = source.link_list(session, course_url)

            print(links)

            for link in links:

                if pattern.search(link[0]) is not None:
                    # request file http header
                    file_request = session.head(link[1], allow_redirects=True)

                    # get file name
                    if 'Content-Disposition' in file_request.headers:
                        file_disposition = file_request.headers['Content-Disposition']
                        file_name = file_disposition[
                                    file_disposition.index('filename=') + 10:len(file_disposition) - 1].encode(
                            'latin-1').decode('utf8')
                    else:
                        file_name = link[0]

                    # check extension
                    if 'ext' in course and course['ext'] is not False:
                        file_ext = os.path.splitext(file_name)[1]
                        if file_ext != course['ext']:
                            continue

                    # get last modified date as timestamp
                    file_last_modified = int(datetime.strptime(file_request.headers['Last-Modified'],
                                                               '%a, %d %b %Y %H:%M:%S %Z').timestamp())
                    # adjust file name
                    if 'rename' in course and course['rename'] is not False:
                        # find a number
                        num = re.search('\d{1,2}', link[0])
                        if num is None:
                            num = re.search('\d{1,2}', file_name)
                        if num is None:
                            num = file_last_modified
                        else:
                            num = num.group(0)
                        file_name = course['rename'].replace('%', str(num))

                    # fetch old timestamp from database
                    file_last_modified_old = c.execute(
                        'SELECT last_modified FROM file_modifications WHERE course=? AND file_name=?',
                        (course['name'], file_name)).fetchone()

                    # save file and timestamp in the database if it doesn't exists
                    if not simulate and file_last_modified_old is None:
                        c.execute('INSERT INTO file_modifications (course, file_name, last_modified) VALUES (?,?,?)',
                                  (course['name'], file_name, file_last_modified))
                    # update timestamp if there's a newer version of the file
                    elif not simulate and file_last_modified > file_last_modified_old[0]:
                        c.execute('UPDATE file_modifications SET last_modified=? WHERE course=? and file_name=?',
                                  (file_last_modified, course['name'], file_name))
                    # otherwise skip saving
                    else:
                        skip_count += 1
                        log(file_name + ' (skipped)')
                        continue

                    log(file_name + ' (new)')

                    if simulate:
                        continue

                    # request whole file
                    file_request = session.get(link[1])

                    file_name = os.path.join(course['local_folder'], file_name)

                    # write file
                    try:
                        os.makedirs(os.path.dirname(file_name), exist_ok=True)
                        with open(file_name, 'wb') as f:
                            f.write(file_request.content)
                            download_count += 1
                    except FileNotFoundError:
                        print('Can\'t write file to %s' % os.path.join(course['local_folder'], file_name))
                        conn.rollback()

                    # save changes to the database
                    conn.commit()

    # display count of downloaded files
    log('\nDownloaded %i file(s), skipped %i file(s)' % (download_count, skip_count))


def clear_course():
    if course_to_clear[0] == 'all':
        c.execute("DELETE from file_modifications")
        log('\nCleared all courses')
    else:
        c.execute("DELETE from file_modifications WHERE course=?", course_to_clear)
        log('\nCleared course %s' % course_to_clear[0])
    conn.commit()


# command line args
parser = argparse.ArgumentParser(description='A simple script for downloading slides and exercises from moodles.')
parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
parser.add_argument('-c', '--course', action='append', help='specify a course which should be checked')
parser.add_argument('-s', '--source', action='append', help='specify a source which should be checked')
parser.add_argument('--simulate', action='store_true', help='specify if the process should only be simulated')
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
        moodle TEXT,
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
