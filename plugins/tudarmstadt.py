import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from lib.source import Login, Source, Link


class TUDarmstadtSSOLogin(Login):
    url = 'https://sso.hrz.tu-darmstadt.de/login'

    def login(self, session, username, password):
        if not self.is_logged_in(session):
            response = session.get(self.url)
            # borrowed from Dominik
            match = re.search(r'<input type="hidden" name="lt" value="(.*?)" />', response.text)
            token = match.group(1)
            match = re.search(r'name="execution" value="(.*?)"', response.text)
            execution = match.group(1)
            # do the real login
            params = {'username': username, 'password': password, 'lt': token,
                      'execution': execution, '_eventId': 'submit',
                      'submit': 'ANMELDEN'}
            session.post(response.url, params)

    def is_logged_in(self, session):
        response = session.get(self.url).text
        return response.find("Log In Successful") != -1 or response.find("Anmeldung erfolgreich") != -1


class TUDarmstadtMoodle(Source):
    def get_links(self, html, url):
        return html.find(id='region-main').findAll('a')

    def link_list(self, session, url):
        # link list
        link_list = []

        html = BeautifulSoup(session.get(url).text, 'html.parser')

        # get all links
        links = self.get_links(html, url)

        # loop through links
        for link in links:
            if link is not None and link.has_attr('href') and link['href'].find('resource') != -1:
                link_list.append(Link(text=link.get_text(), url=link['href']))
        return link_list

    def login(self, session, login_url, username, password):
        sso = TUDarmstadtSSOLogin()
        sso.login(session, username, password)
        session.get(login_url)

    def course_url(self, url, param):
        return urljoin(url, '/course/view.php?id=' + str(param))


class TUDarmstadtFacultySite(Source):
    def get_links(self, html, url):
        return html.findAll('a')

    def login(self, session, login_url, username, password):
        sso = TUDarmstadtSSOLogin()
        sso.login(session, username, password)
        session.get(login_url)

    def course_url(self, url, param):
        return urljoin(url, param)
