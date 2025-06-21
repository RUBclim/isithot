from datetime import date

import pandas as pd
from flask_sqlalchemy import SQLAlchemy

from isithot import ColumnMapping
from isithot import create_app
from isithot import DataProvider
from isithot.cache import cache

db = SQLAlchemy()


class Lmss(DataProvider):
    @cache.cached(timeout=300, key_prefix='daily_data')
    def get_daily_data(self, d: date) -> pd.DataFrame:
        """Get the daily data for the LMSS from the database

        :param d: the date for which to prepare data. This will usually be
            today
        """
        daily_query = '''\
            SELECT
                date::TIMESTAMP,
                temp_mean_mannheim,
                EXTRACT(DOY FROM date) AS doy
            FROM lmss_daily ORDER BY date
        '''
        return pd.read_sql(sql=daily_query, con=db.engine, index_col='date')

    @cache.cached(timeout=300, key_prefix='current_data')
    def get_current_data(self, d: date) -> pd.DataFrame:
        """Get today's data for the LMSS from the database

        :param d: the date for which to prepare data. This will usually be
            today
        """
        now_query = '''\
            SELECT
                date, temp_max, temp_min
            FROM lmss_garden_raw
            WHERE date > %(date)s
            ORDER BY date
        '''
        return pd.read_sql(
            sql=now_query,
            con=db.engine,
            index_col='date',
            params={'date': d},
        )


if __name__ == '__main__':
    from isithot.config import Config

    COL_MAPPING = ColumnMapping(
        datetime='date',
        temp_mean='temp_mean_mannheim',
        temp_max='temp_max',
        temp_min='temp_min',
        day_of_year='doy',
    )

    DATA_PROVIDERS: dict[str, DataProvider] = {
        'lmss': Lmss(
            col_mapping=COL_MAPPING,
            name='LMSS',
            min_year=2010,
            id='lmss',
        ),
    }
    app = create_app(Config)
    db.init_app(app)

    # Register the data providers
    app.config['DATA_PROVIDERS'] = DATA_PROVIDERS
    with app.app_context():
        app.run(debug=True)
