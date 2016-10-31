from urllib.parse import urljoin

from bs4 import BeautifulSoup

from lib.source import Source


class SimpleSite(Source):
    def get_links(self, session, url):
        return BeautifulSoup(session.get(url).text, 'html.parser').findAll('a')

    def login(self, session, login_url, username, password):
        pass

    def course_url(self, url, param):
        return urljoin(url, param)
