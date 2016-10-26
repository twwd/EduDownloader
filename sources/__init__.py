import re
from abc import ABC, abstractmethod
from collections import namedtuple

Link = namedtuple('Link', ['title', 'filename', 'url'])


class Source(ABC):
    @abstractmethod
    def login(self, session, login_url, username, password):
        pass

    @abstractmethod
    def generate_link_list(self, session, url):
        pass


class Login(ABC):
    @abstractmethod
    def login(self, session, username, password):
        pass


class TUDarmstadtSSOLogin(Login):
    url = 'https://sso.hrz.tu-darmstadt.de/login'

    def login(self, session, username, password):
        if not self.is_logged_in(self, session):
            response = session.get(self.url)
            # borrowed from Dominik
            match = re.search(r'<input type="hidden" name="lt" value="(.*?)" />', response.text)
            token = match.group(1)
            match = re.search(r'name="execution" value="(.*?)"', response.text)
            execution = match.group(1)
            # do the real login
            params = {'username': username, 'password': 'password', 'lt': token,
                      'execution': execution, '_eventId': 'submit',
                      'submit': 'ANMELDEN'}
            session.post(response.url, params)

    def is_logged_in(self, session):
        response = session.get(self.url)
        return response.find("Log In Successful") != -1 or response.find("Anmeldung erfolgreich") != -1


class TUDarmstadtInformatikMoodle(Source):
    def generate_link_list(self, session, url):
        pass

    def login(self, session, login_url, username, password):
        pass


class TUDarmstadtMoodle(Source):
    def generate_link_list(self, session, url):
        pass

    def login(self, session, login_url, username, password):
        pass


class TUDarmstadtFacultySite(Source):
    def generate_link_list(self, session, url):
        pass

    def login(self, session, login_url, username, password):
        pass


class SimpleSite(Source):
    def generate_link_list(self, session, url):
        pass

    def login(self, session, login_url, username, password):
        pass
