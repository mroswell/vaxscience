document.addEventListener("DOMContentLoaded", function() {
    const suggested_facets = document.querySelector('.suggested-facets');
    suggested_facets.innerHTML = suggested_facets.innerHTML.replace(/ (\(array\)|\(date\))/g, '')
});
