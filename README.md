[![CI](https://github.com/RUBclim/isithot/actions/workflows/CI.yaml/badge.svg)](https://github.com/RUBclim/isithot/actions?query=workflow%3ACI)
[![deploy docs to gh-page](https://github.com/RUBclim/isithot/actions/workflows/pages.yaml/badge.svg)](https://github.com/RUBclim/isithot/actions/workflows/pages.yaml)

# isithot

## Installation

via https

```bash
pip install git+https://github.com/RUBclim/isithot
```

via ssh

```bash
pip install git+ssh://git@github.com/RUBclim/isithot
```

## Quick start

An initial app can be create quite simple by adding a single data provider.

### Adding data providers

1. Add a new `isithot.DataProvider` instance. The `DataProvider.get_current_data` and
   `DataProvider.get_daily_data` methods need to be implemented.
1. Create a `isithot.ColumnMapping` instance which maps the columns of your data source
   to the columns the package expects.
1. Create a dictionary of `isithot.DataProvider` where the key must match the `id`.
1. register the data providers with the current app
   `app.config['DATA_PROVIDERS'] = data_providers`.

see the [full documentation](https://rubclim.github.io/isithot/)

```python
from datetime import date

import pandas as pd
from flask import Flask
from isithot import ColumnMapping
from isithot import create_app
from isithot import DataProvider
from isithot.config import Config


class TestProvider(DataProvider):
    def get_current_data(self, d: date) -> pd.DataFrame:
        df = pd.DataFrame({
            'date': [pd.Timestamp(d)],
            'temp_max': [30.0],
            'temp_min': [20.0],
        })
        return df.set_index('date')

    def get_daily_data(self, d: date) -> pd.DataFrame:
        x = pd.read_csv(
            'testing/monthly_input_data/lmss_daily_long.csv',
            parse_dates=['date'],
            index_col='date',
        )
        x['doy'] = x.index.dayofyear
        return x


def my_app() -> Flask:
    col_map = ColumnMapping(
        datetime='date',
        temp_mean='temp_mean_mannheim',
        temp_max='temp_max',
        temp_min='temp_min',
        day_of_year='doy',
    )

    data_providers = {
        'test': TestProvider(
            col_mapping=col_map,
            name='Test',
            id='test',
            min_year=2010,
        ),
    }

    app = create_app(Config)
    app.config['DATA_PROVIDERS'] = data_providers
    return app


if __name__ == '__main__':
    app = my_app()
    app.run(debug=True)
```
