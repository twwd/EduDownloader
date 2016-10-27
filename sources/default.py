from abc import ABC, abstractmethod
from collections import namedtuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

Link = namedtuple('Link', ['text', 'url'])


class Source(ABC):
    @abstractmethod
    def login(self, session, login_url, username, password):
        pass

    @abstractmethod
    def link_list(self, session, url):
        pass

    @abstractmethod
    def course_url(self, url, param):
        pass


class Login(ABC):
    @abstractmethod
    def login(self, session, username, password):
        pass


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
            link_list.append(Link(text=link.get_text(), url=urljoin(url, link['href'])))
        return link_list

    def login(self, session, login_url, username, password):
        pass

    def course_url(self, url, param):
        return urljoin(url, param)
