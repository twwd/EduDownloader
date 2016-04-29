#!/usr/bin/env python3
import os
import re
from urllib.parse import urljoin

import requests
import yaml
from bs4 import BeautifulSoup

debug = True

# import config
with open(os.path.join('data', 'config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)
    # disable HTTPS warnings
    requests.packages.urllib3.disable_warnings()
    # make the initial request to get the token
    session = requests.Session()

    # Loop through moodles
    for moodle in config:
        if debug:
            print('\nCurrent moodle is %s' % moodle['name'])

        # login
        response = session.get(urljoin(moodle['base_url'], 'my'), allow_redirects=False)
        # check if the user is already signed in
        # TODO
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
            if debug:
                print(course['name'])
            course_url = urljoin(moodle['base_url'], '/course/view.php?id=' + str(course['id']))
            course_content = BeautifulSoup(session.get(course_url).text, 'html.parser').find(id='region-main')
            for link_text in course_content.find_all(string=re.compile(course['pattern'])):
                link = link_text.find_parent('a')
                if link is not None:
                    file_request = session.get(link['href'])
                    file_disposition = file_request.headers['Content-Disposition']
                    file_name = file_disposition[
                                file_disposition.index('filename=') + 10:len(file_disposition) - 1].encode(
                        "latin-1").decode("utf8")
                    if debug:
                        print(file_name)
                    with open(os.path.join(course['local_folder'], file_name), 'wb') as f:
                        f.write(file_request.content)
