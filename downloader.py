#!/usr/bin/env python3
import os
import re
import sqlite3
from datetime import datetime
from urllib.parse import urljoin

import requests
import yaml
from bs4 import BeautifulSoup

verbose_output = True
download_count = 0
skip_count = 0

# database for timestamps
conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), 'data', 'timestamps.db'))
c = conn.cursor()

# check if table exists otherwise create it
try:
    c.execute('SELECT * FROM timestamp')
except sqlite3.OperationalError:
    if verbose_output:
        print("create table")
    c.execute(
        '''
        CREATE TABLE `timestamp` (
            `id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            `course`	TEXT,
            `file_name`	TEXT,
            `last_modified`	INTEGER
        );
        ''')

# import config
with open(os.path.join(os.path.dirname(__file__), 'data', 'config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)
    # disable HTTPS warnings
    requests.packages.urllib3.disable_warnings()
    # make the initial request to get the token
    session = requests.Session()

    # Loop through moodles
    for moodle in config:
        if verbose_output:
            print('\nMoodle: %s' % moodle['name'])

        # login
        response = session.get(urljoin(moodle['base_url'], 'my'), allow_redirects=False)
        # check if the user is already signed in
        if response.status_code != 301:
            response = session.get(moodle['login_url'])
            # borrowed from Dominik
            match = re.search(r'<input type="hidden" name="lt" value="(.*?)" />', response.text)
            token = match.group(1)
            match = re.search(r'name="execution" value="(.*?)"', response.text)
            execution = match.group(1)
            # do the real login
            params = {"username": moodle['username'], "password": moodle['password'], "lt": token,
                      "execution": execution, "_eventId": "submit",
                      "submit": "ANMELDEN"}
            session.post(response.url, params)

        # loop through courses
        for course in moodle['courses']:

            if verbose_output:
                print('Course: %s' % course['name'])

            course_url = urljoin(moodle['base_url'], '/course/view.php?id=' + str(course['id']))
            # search only main content
            course_content = BeautifulSoup(session.get(course_url).text, 'html.parser').find(id='region-main')

            for link_text in course_content.find_all(string=re.compile(course['pattern'])):
                link = link_text.find_parent('a')
                if link is not None and link['href'].find('resource') != -1:
                    # request file http header
                    file_request = session.head(link['href'], allow_redirects=True)

                    # get file name
                    if 'Content-Disposition' in file_request.headers:
                        file_disposition = file_request.headers['Content-Disposition']
                        file_name = file_disposition[
                                    file_disposition.index('filename=') + 10:len(file_disposition) - 1].encode(
                            "latin-1").decode("utf8")
                    else:
                        file_name = link_text

                    # get last modified date as timestamp
                    file_last_modified = int(datetime.strptime(file_request.headers['Last-Modified'],
                                                               '%a, %d %b %Y %H:%M:%S %Z').timestamp())
                    # adjust file name
                    if 'rename' in course and course['rename'] is not False:
                        # find a number
                        num = re.search('\d{1,2}', link_text)
                        if num is None:
                            num = re.search('\d{1,2}', file_name)
                        if num is None:
                            num = file_last_modified
                        else:
                            num = num.group(0)
                        file_name = course['rename'].replace('%', str(num))

                    # fetch old timestamp from database
                    file_last_modified_old = c.execute(
                        'SELECT last_modified FROM timestamp WHERE course=? AND file_name=?',
                        (course['name'], file_name)).fetchone()

                    # save file and timestamp in the database if it doesn't exists
                    if file_last_modified_old is None:
                        c.execute('INSERT INTO timestamp (course, file_name, last_modified) VALUES (?,?,?)',
                                  (course['name'], file_name, file_last_modified))
                    # update timestamp if there's a newer version of the file
                    elif file_last_modified > file_last_modified_old[0]:
                        c.execute('UPDATE timestamp SET last_modified=? WHERE course=? and file_name=?',
                                  (file_last_modified, course['name'], file_name))
                    # otherwise skip saving
                    else:
                        skip_count += 1
                        if verbose_output:
                            print(file_name + ' (skipped)')
                        continue

                    if verbose_output:
                        print(file_name + ' (new)')

                    # save changes to the database
                    conn.commit()

                    # request whole file
                    file_request = session.get(link['href'])

                    # write file
                    with open(os.path.join(course['local_folder'], file_name), 'wb') as f:
                        f.write(file_request.content)
                        download_count += 1

# display count of downloaded files
print('\nDownloaded %i file(s), skipped %i file(s)' % (download_count, skip_count))
