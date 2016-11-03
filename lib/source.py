from abc import ABC, abstractmethod
from collections import namedtuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

Link = namedtuple('Link', ['text', 'url'])


class Source(ABC):
    @abstractmethod
    def login(self, session, login_url, username, password):
        pass

    def link_list(self, session, url):
        # link list
        link_list = []

        html = BeautifulSoup(session.get(url).text, 'html.parser')

        # look for the base element
        base = html.find('base')

        # get all links
        links = self.get_links(html, url)

        if base is not None and base.has_attr('href'):
            print("Base tag found")
            url = base['href']

        # loop through links
        for link in links:
            if link.has_attr('href'):
                link_list.append(Link(text=link.get_text().replace(u'\xa0', u' '), url=urljoin(url, link['href'])))

        return link_list

    @abstractmethod
    def get_links(self, html, url):
        return []

    @abstractmethod
    def course_url(self, url, param):
        pass


class Login(ABC):
    @abstractmethod
    def login(self, session, username, password):
        pass
