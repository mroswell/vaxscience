# vaxscience

```% python3 transform.py | jq --monochrome-output . >articles2.transformed.json
```

```
% brew install sqlite-utils
% sqlite-utils insert articles1.db articles - --pk ID <articles2.transformed.json
```

```
%  sqlite-utils transform articles1.db articles \
    --column-order Section \
    --column-order Subsection \
    --column-order Title \
    --column-order Link\(s\) \
    --column-order Abstract \
    --column-order MeSH \
    --column-order Author\(s\) \
    --column-order Affiliation \
    --column-order PMID \
    --column-order PMCID \
    --column-order PubDate \
    --column-order article_title
```
```
% datasette articles1.db         --setting default_page_size 3000 \
        --setting max_returned_rows 3000 \
        --setting default_facet_size 3000
```
