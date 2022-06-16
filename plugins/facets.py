import urllib.parse
from datasette import hookimpl, utils


def absolute_url(request, path):
    return urllib.parse.urljoin(request.url, path)


def qs_key(value):
    return f'_facet_{value.get("type", "")}'.rstrip('_')


@hookimpl
def extra_template_vars(request):
    columns = [
        {'name': 'Section'},
        {'name': 'PubType'},
        {'name': 'PubDate', 'type': 'date'},
        {'name': 'Main_Topic', 'type': 'array'},
        {'name': 'Demographics', 'type': 'array'},
        {'name': 'MeSH', 'type': 'array'},
        {'name': 'Author(s)', 'type': 'array'},
        {'name': 'Affiliation', 'type': 'array'},
    ]

    suggested_facets = [
        {
            'name': column['name'],
            'type': column.get('type', ''),
            'toggle_url': absolute_url(
                request,
                utils.path_with_added_args(
                    request,
                    {qs_key(column): column['name']}
                )
            )
        }
        for column in columns
    ]

    return {"suggested_facets": suggested_facets}
