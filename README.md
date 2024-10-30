## Installing into your dev AA

Once you have cloned or copied all files into place and finished renaming the app you are ready to install it to your dev AA instance.

Make sure you are in your venv. Then install it with pip in editable mode:

```bash
pip install -e aa-contra
```

First add your app to the Django project by adding the name of your app to INSTALLED_APPS in `settings/local.py`.

Next we will create new migrations for your app:

```bash
python manage.py makemigrations
```

Then run a check to see if everything is setup correctly.

```bash
python manage.py check
```

In case they are errors make sure to fix them before proceeding.

Next perform migrations to add your model to the database:

```bash
python manage.py migrate
```

Finally restart your AA server and that's it.

## Installing into production AA

To install your plugin into a production AA run this command within the virtual Python environment of your AA installation:

```bash
pip install git+https://github.com/karaboznolm/aa-contra
```

Alternatively you can create a package file and manually deliver it to your production AA:

```bash
python -m build
```

And then install it directly from the package file

```bash
pip install your-package-app.tar.gz
```

Then add your app to `INSTALLED_APPS` in `settings/local.py`, run migrations and restart your allianceserver.

## Contribute

If you made a new app for AA please consider sharing it with the rest of the community. For any questions on how to share your app please contact the AA devs on their Discord. You find the current community creations [here](https://gitlab.com/allianceauth/community-creations).
