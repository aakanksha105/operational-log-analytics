from __future__ import annotations

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def app():
    app = create_app()

    app.config.update(
        TESTING=True,
    )

    with app.app_context():
        db.create_all()

        yield app


@pytest.fixture()
def client(app):
    return app.test_client()