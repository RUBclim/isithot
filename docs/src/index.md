# Welcome to isithot documentation!

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

1. Add a new {class}`isithot.DataProvider` instance. The
   {meth}`DataProvider.get_current_data` and {meth}`DataProvider.get_daily_data` methods
   need to be implemented.
1. Create a {class}`isithot.ColumnMapping` instance which maps the columns of your data
   source to the columns the package expects.
1. Create a dictionary of {class}`isithot.DataProvider` where the key must match the
   `id`.
1. register the data providers with the current app
   `app.config['DATA_PROVIDERS'] = data_providers`.

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

### implementing caching

The `isithot` app comes with caches that can be added to a function. E.g. the daily data
will likely not changes very often, hence we can cache it for e.g. one hour.

```python
from isithot.cache import cache

class TestProvider(DataProvider):
    @cache.cached(timeout=60*60, key_prefix='daily_data')
    def get_daily_data(self, d: date) -> pd.DataFrame:
        ...
```

### more complex data retrieval

An example for a more complex example can be found in
[`testing/example_app.py`](https://github.com/RUBclim/isithot/blob/main/testing/example_app.py)
which uses database queries. All implementations need to consider performance since this
is executed during handling of the http request.

Another option for data retrieval is the server performing and API request e.g.

```python
    def get_current_data(self, d: date) -> DataFrame:
        """
        fetch the latest weather data from the DWD. ``self.id`` corresponds to the
        station ID by DWD which is set during DataProvider creation.
        """
        ret = urllib.request.urlopen(
            f'https://dwd.api.proxy.bund.dev/v30/stationOverviewExtended?stationIds={self.id}',
            timeout=3,
        )
        data = current_app.json.loads(ret.read())
        temp_min = data[self.id]['days'][0]['temperatureMin'] / 10
        temp_max = data[self.id]['days'][0]['temperatureMax'] / 10
        date = datetime.strptime(
            data[self.id]['days'][0]['dayDate'], '%Y-%m-%d',
        )
        return pd.DataFrame(
            {
                self.col_mapping.temp_min: temp_min,
                self.col_mapping.temp_max: temp_max,
            },
            index=pd.DatetimeIndex([date], name=self.col_mapping.datetime),
        )
```

## API-Documentation

### i18n

This web-app uses internationalization (i18n) to also have this page available in
german, since the audience will mostly be german. This is setup via `Babel` and all
english text (both, in `.py` and `.html` files) is wrapped in `_(...)` a function. This
can be extracted automatically via:

```bash
pybabel extract -F babel.cfg -o isithot/translations/messages.pot .
```

This will generate a `messages.pot` file which is the basis for all translations. Based
on this a translation can be initialized with this command. In this case this is for
German (`de`).

```bash
pybabel init -i isithot/translations/messages.pot -d isithot/translations/ -l de
```

This will now create a subfolder for the specific language (in this case `de` for
German). The `messages.pot` can now be used to translate all messages.

Finally, the languages have to be compiled into a `messages.mo` file. This needs to be
done manually for testing. It is done automatically for production while building the
docker image.

```bash
pybabel compile -d isithot/translations
```

````{important}
   If there are changes made to any of the strings (in the `.py` or `.html` file
   that are wrapped in a `_(...)` function) the `.pot` file needs to be updated
   using these commands:

   ```bash
   pybabel extract -F babel.cfg -o isithot/translations/messages.pot .
   ```

   ```bash
   pybabel update -i isithot/translations/messages.pot -d isithot/translations
   ```

````

## `app`

```{eval-rst}
.. automodule:: isithot.app
   :members:
   :undoc-members:
```

## `blueprints`

```{eval-rst}
.. automodule:: isithot.blueprints.isithot
   :members:
   :undoc-members:
```

```{eval-rst}
.. automodule:: isithot.blueprints.plots
   :members:
   :undoc-members:
```

## Indices and tables

- {ref}`search`
- {ref}`genindex`
