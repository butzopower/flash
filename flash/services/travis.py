"""Defines the Travis CI service integrations."""

import logging

import requests

from .core import Service
from .utils import naturaldelta, truncate

logger = logging.getLogger(__name__)


class TravisOS(Service):
    """Show the current status of an open-source project.

    Arguments:
      account (:py:class:`str`): The name of the account.
      app (:py:class:`str`): The name of the application.

    Attributes:
      repo (:py:class:`str`): The repository name, in the format
        ``account/application``.

    """

    OUTCOMES = {
        'canceled': 'cancelled',
        'failed': 'failed',
        'passed': 'passed',
        '?': 'crashed',
        '??': 'working',
    }
    REQUIRED = {'account', 'app'}
    ROOT = 'https://api.travis-ci.org'
    TEMPLATE = 'travis'

    def __init__(self, *, account, app, **kwargs):
        super().__init__(**kwargs)
        self.account = account
        self.app = app
        self.repo = '{}/{}'.format(account, app)

    @property
    def headers(self):
        headers = super().headers
        headers.update({
            'Accept': 'application/vnd.travis-ci.2+json',
            'User-Agent': 'Flash',
        })
        return headers

    def update(self):
        logger.debug('fetching TravisCI project data')
        response = requests.get(
            self._url_builder('/repos/{repo}/builds', {'repo': self.repo}),
            headers=self.headers,
        )
        if response.status_code == 200:
            return self.format_data(response.json())
        logger.error('failed to update TravisCI project data')
        return {}

    def format_data(self, data):
        commits = {commit['id']: commit for commit in data.get('commits', [])}
        return dict(
            name=self.repo,
            builds=[
                self.format_build(bld, commits.get(bld.get('commit_id'), {}))
                for bld in data.get('builds', [])
            ]
        )

    @classmethod
    def format_build(cls, build, commit):
        status = build.get('state')
        if status not in cls.OUTCOMES:
            logger.warning('unknown status: %s', status)
        try:
            elapsed = 'took {}'.format(naturaldelta(int(build.get('duration'))))
        except (TypeError, ValueError):
            logger.exception('failed to generate elapsed time')
            elapsed = 'elapsed time not available'
        return dict(
            author=commit.get('author_name'),
            elapsed=elapsed,
            message=truncate(commit.get('message', '')),
            outcome=cls.OUTCOMES.get(status),
        )