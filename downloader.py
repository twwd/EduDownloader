#!/usr/bin/env python3
import os
import re
import sqlite3
from urllib.parse import urljoin

import requests
# Connect to database
from bs4 import BeautifulSoup

conn = sqlite3.connect(os.path.join('data', 'moodle_downloader.db'))
c = conn.cursor()
c2 = conn.cursor()

# disable HTTPS warnings
requests.packages.urllib3.disable_warnings()
# make the initial request to get the token
session = requests.Session()

# Loop through moodles
for moodle in c2.execute('SELECT * FROM moodle'):
    print('Current moodle is %s' % moodle[1])
    # login
    response = session.get(moodle[2])
    if response.url != '' and response.text.find('Anmeldung erfolgreich') == -1:
        print('do login')
        print(response.url)
        # lent from Dominik
        match = re.search(r'<input type="hidden" name="lt" value="(.*?)" />', response.text)
        token = match.group(1)
        match = re.search(r'name="execution" value="(.*?)"', response.text)
        execution = match.group(1)
        # do the real login
        params = {"username": moodle[3], "password": moodle[4], "lt": token,
                  "execution": execution, "_eventId": "submit",
                  "submit": "ANMELDEN"}
        response = session.post(response.url, params)
        response = session.get(moodle[1])

    for course in c.execute('SELECT * FROM course WHERE moodle=?', (moodle[0],)):
        print(course[5])
        course_url = urljoin(moodle[1], '/course/view.php?id=' + str(course[1]))
        course_content = BeautifulSoup(session.get(course_url).text, 'html.parser').find(id='region-main')
        for link_text in course_content.find_all(string=re.compile(course[3])):
            link = link_text.find_parent('a')
            if link is not None:
                print(link['href'])
