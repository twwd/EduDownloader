#!/usr/bin/env python3
import os
import re
import sqlite3
from urllib.parse import urljoin

import requests

# Connect to database
conn = sqlite3.connect(os.path.join('data', 'moodle_downloader.db'))
c = conn.cursor()

# disable HTTPS warnings
requests.packages.urllib3.disable_warnings()
# make the initial request to get the token
session = requests.Session()

# Loop through moodles
for moodle in c.execute('SELECT * FROM moodle'):
    # login
    response = session.get(moodle[2], allow_redirects=True)
    if response.text.find('Anmeldung erfolgreich') == -1:
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
        course_url = urljoin(moodle[1], '/course/view.php?id=' + str(course[1]))
        print(course_url)
        course_content = session.get(course_url).text
        for file in re.findall(r'Vorlesung.*', course_content):  # '(%s)' % course[2], course_content):
            print(file)
