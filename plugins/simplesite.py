from urllib.parse import urljoin

from lib.source import Source


class SimpleSite(Source):
    def get_links(self, html, url):
        return html.findAll('a')

    def login(self, session, login_url, username, password):
        pass

    def course_url(self, url, param):
        return urljoin(url, param)
