import re
from abc import ABC, abstractmethod
from collections import namedtuple

from bs4 import BeautifulSoup

Link = namedtuple('Link', ['text', 'url'])


class Source(ABC):
    @abstractmethod
    def login(self, session, login_url, username, password):
        pass

    @abstractmethod
    def link_list(self, session, url):
        pass


class Login(ABC):
    @abstractmethod
    def login(self, session, username, password):
        pass


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
    def link_list(self, session, url):
        # link list
        link_list = []

        # search only main content
        course_content = BeautifulSoup(session.get(url).text, 'html.parser').find(id='region-main').findAll('a')

        # loop through links
        for link in course_content:
            if link is not None and link['href'].find('resource') != -1:
                link_list.append(Link(text=link.get_text(), url=link['href']))
        return link_list

    def login(self, session, login_url, username, password):
        sso = TUDarmstadtSSOLogin()
        sso.login(session, username, password)
        session.get(login_url)


class TUDarmstadtFacultySite(Source):
    def link_list(self, session, url):
        pass

    def login(self, session, login_url, username, password):
        sso = TUDarmstadtSSOLogin()
        sso.login(session, username, password)
        session.get(login_url)


class SimpleSite(Source):
    def link_list(self, session, url):
        # link list
        link_list = []

        # search all links
        site_links = BeautifulSoup(session.get(url).text, 'html.parser').findAll('a')

        if site_links is None:
            return

        # loop through links
        for link in site_links:
            link_list.append(Link(text=link.get_text(), url=link['href']))
        return link_list

    def login(self, session, login_url, username, password):
        pass
