from django.contrib.staticfiles.storage import staticfiles_storage
from jinja2 import Environment


def environment(**options):
    env = Environment(extensions=["jinja2.ext.i18n"], **options)
    env.globals.update(
        {
            "static": staticfiles_storage.url,
            # 'url': reverse,
        }
    )
    # env.filters.update({
    #     'a': a,
    # })
    return env
