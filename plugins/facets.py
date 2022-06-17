from urllib.parse import urljoin, parse_qs
from datasette import hookimpl, utils


@hookimpl
def extra_template_vars(request):
    query_string = parse_qs(request.query_string)
    columns = [
        {'name': 'Section'},
        {'name': 'Subsection'},
        {'name': 'Main_Topic', 'type': 'array'},
        {'name': 'MeSH', 'type': 'array'},
        {'name': 'Demographics', 'type': 'array'},
        {'name': 'PubType'},
        {'name': 'Author(s)', 'type': 'array'},
    ]

    suggested_facets = []
    for column in columns:
        name = column['name']
        facet_type = column.get('type')
        facet_key = f'_facet_{facet_type or ""}'.rstrip('_')

        selected = query_string.get(facet_key, [])
        if name in selected:
            continue

        path = utils.path_with_added_args(request, {facet_key: name})
        url = urljoin(request.url, path)
        suggested_facets.append({
            'name': name,
            'type': facet_type,
            'toggle_url': url,
        })

    return {"suggested_facets": suggested_facets}
