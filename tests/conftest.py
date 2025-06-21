import pytest
import sqlalchemy
from sqlalchemy import text

from isithot import ColumnMapping
from isithot import create_app
from isithot import DataProvider
from testing.example_app import db
from testing.example_app import Lmss


@pytest.fixture(scope='session')
def engine():
    engine = sqlalchemy.create_engine(
        'postgresql+psycopg2://dbuser:test@localhost:5432/dev',
        isolation_level='AUTOCOMMIT',
    )
    yield engine
    engine.dispose()


CP_OPTS = {'sep': ',', 'null': ''}


@pytest.fixture
def raw_table_data(engine):
    with engine.connect() as con:
        cursor = con.connection.cursor()
        with open('testing/raw/lmss_garden_raw.csv') as lmss_garden:
            header = next(lmss_garden).strip().split(',')
            cursor.copy_from(
                lmss_garden,
                table='lmss_garden_raw',
                columns=header,
                **CP_OPTS,
            )
    yield
    with engine.connect() as con:
        con.execute(text('DELETE FROM lmss_garden_raw'))


@pytest.fixture
def clean_tables(engine):
    yield
    with engine.connect() as con:
        con.execute(text('DELETE FROM lmss_garden_raw'))
        con.execute(text('DELETE FROM lmss_daily'))


@pytest.fixture
def isithot_client():
    class Config:
        SECRET_KEY = 'testing'
        TESTING = True
        SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://dbuser:test@localhost:5432/dev'  # noqa: E501
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        CACHE_TYPE = 'SimpleCache'
        CACHE_DEFAULT_TIMEOUT = 0

    app = create_app(Config)
    db.init_app(app)
    col_mapping = ColumnMapping(
        datetime='date',
        temp_mean='temp_mean_mannheim',
        temp_max='temp_max',
        temp_min='temp_min',
        day_of_year='doy',
    )

    data_providers: dict[str, DataProvider] = {
        'lmss': Lmss(
            col_mapping=col_mapping,
            name='LMSS',
            id='lmss',
            min_year=2010,
        ),
    }
    app = create_app(Config)
    db.init_app(app)

    # Register the data providers
    app.config['DATA_PROVIDERS'] = data_providers

    with app.test_client() as client:
        yield client
