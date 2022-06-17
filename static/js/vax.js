document.addEventListener("DOMContentLoaded", function() {
    const suggested_facets = document.querySelector('.suggested-facets');
    suggested_facets.innerHTML = suggested_facets.innerHTML.replace(/ (\(array\)|\(date\))/g, '')

    const facet_names = [
        'Section',
        'Subsection',
        'Main_Topic',
        'MeSH',
        'Demographics',
        'PubType',
        'Author(s)'
    ];
    const facet_results = document.querySelector('.facet-results');
    if (facet_results) {
        const facets = {};
        facet_results.querySelectorAll('.facet-info').forEach(function(elem) {
            const name = elem.querySelector('.facet-info-name').textContent
                .trim()
                .split('\n')[0]
                .replace(/\((array|date)\)/g, '')
                .trim();
            facets[name] = elem;
        });
        facet_results.innerHTML = '';
        facet_names.forEach(function(name) {
            if (facets[name]) {
                facet_results.appendChild(facets[name]);
            }
        });
    }
});
