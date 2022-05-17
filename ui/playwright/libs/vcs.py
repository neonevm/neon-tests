import abc
import enum
import logging
import typing as tp

import pytest
import requests

from tests.bench.tf_runs.parser import Html2ElementTree

LOG = logging.getLogger(__name__)


class VCSProvider(metaclass=abc.ABCMeta):
    name: str = None

    def __init__(self):
        self._session = requests.Session()
        self._parser = Html2ElementTree()

    @abc.abstractmethod
    def login(self, login: str, password: str):
        raise NotImplementedError

    @abc.abstractmethod
    def create_oauth(self, name: str, callback_url: str, homepage: str):
        raise NotImplementedError

    @abc.abstractmethod
    def delete_oauth(self, name: str):
        raise NotImplementedError


class VCSGitHub(VCSProvider):

    name = "GitHub"

    def login(self, login: str, password: str) -> requests.Response:
        tree = self._parser.parse(self._session.get("https://github.com/login").text)
        fields = {}
        form = tree.find('.//form[@action="/session"]')
        inputs = form.findall(".//input[@type='hidden']") + form.findall(".//input[@type='text']")
        for field in inputs:
            fields[field.attrib["name"]] = field.attrib.get("value", "")
        fields["login"] = login
        fields["password"] = password
        fields["webauthn-support"] = "supported"
        fields["webauthn-iuvpaa-support"] = "unsupported"
        return self._session.post("https://github.com/session", data=fields)

    def list_oauth(self):
        tree = self._parser.parse(self._session.get("https://github.com/settings/developers").text)
        apps = tree.findall('.//div[@class="TableObject"]//a[@class="text-bold"]')
        return [a.text for a in apps]

    def create_oauth(
        self, name: str, callback_url: str, homepage: str = "https://scalr.io"
    ) -> requests.Response:
        LOG.debug("Open GitHub application page")
        resp = self._session.get("https://github.com/settings/applications/new")
        LOG.debug(f"Response: {resp.status_code}")

        tree = self._parser.parse(resp.text)
        fields = {}
        form = tree.find(".//form[@id='new_oauth_application']")
        inputs = form.findall(".//input[@type='hidden']") + form.findall(".//input[@type='text']")
        for field in inputs:
            fields[field.attrib["name"]] = field.attrib.get("value", "")
        fields["oauth_application[name]"] = name
        fields["oauth_application[url]"] = homepage
        fields["oauth_application[callback_url]"] = callback_url
        return self._session.post("https://github.com/settings/applications", data=fields)

    def delete_oauth(self, name: str):
        tree = self._parser.parse(self._session.get("https://github.com/settings/developers").text)
        apps = tree.findall(".//a")
        app_id = None
        for app in apps:
            if app.text == name:
                app_id = app.attrib["href"].split("/")[-1]
        if app_id is None:
            raise AssertionError(f"OAuth with name {name} not found")
        app_tree = self._parser.parse(
            self._session.get(f"https://github.com/settings/applications/{app_id}/advanced").text
        )
        fields = {}
        form = app_tree.find('.//button[@class="btn-danger btn"]/..')
        inputs = form.findall(".//input[@type='hidden']") + form.findall(".//input[@type='text']")
        for field in inputs:
            fields[field.attrib["name"]] = field.attrib.get("value", "")
        return self._session.post(f"https://github.com{form.attrib['action']}", data=fields)

    def authorize_app(self, url: str):
        """Authorize application for user (first oauth redirect)"""
        tree = self._parser.parse(self._session.get(url).text)
        fields = {}
        form = tree.find(".//form")
        inputs = form.findall(".//input[@type='hidden']") + form.findall(".//input[@type='text']")
        for field in inputs:
            fields[field.attrib["name"]] = field.attrib.get("value", "")
        fields["authorize"] = 1
        return self._session.post(
            f"https://github.com{form.attrib['action']}", data=fields, allow_redirects=False
        )

    def get_app_settings(self, name: str):
        """Return OAuth settings (key, secret)"""
        tree = self._parser.parse(self._session.get("https://github.com/settings/developers").text)
        apps = tree.findall(".//a")
        app_id = None
        for app in apps:
            if app.text == name:
                app_id = app.attrib["href"].split("/")[-1]
        if app_id is None:
            raise AssertionError(f"OAuth with name {name} not found")
        app_tree = self._parser.parse(
            self._session.get(f"https://github.com/settings/applications/{app_id}").text
        )

        new_secret_form = app_tree.find('.//input[@value="Generate a new client secret"]/..')
        token = new_secret_form.find('.//input[@name="authenticity_token"]').attrib["value"]

        tree = self._parser.parse(
            self._session.post(
                f"https://github.com{new_secret_form.attrib['action']}",
                data={"authenticity_token": token},
            ).text
        )
        secret = tree.find('.//code[@id="new-oauth-token"]')
        settings = {"key": tree.find('.//code[@class="f4"]').text, "secret": secret.text}
        return settings


class Providers(enum.Enum):
    github = VCSGitHub
