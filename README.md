# vaxscience
```
python3 transform.py | python3 -mjson.tool >articles.transformed.json
```

```
% python3 transform.py | jq --monochrome-output . >articles.transformed.json
```

```
% brew install sqlite-utils
% sqlite-utils insert articles.db articles - --pk ID <articles.transformed.json
```

```
sqlite-utils transform articles.db articles \
    --column-order Main_Topic \
    --column-order Title \
    --column-order Link\(s\) \
    --column-order Demographics \
    --column-order Abstract \
    --column-order MeSH \
    --column-order Author\(s\) \
    --column-order Affiliation \
    --column-order PMID \
    --column-order PMCID \
    --column-order PubDate \
    --column-order article_title \
    --column-order Section \
    --column-order Subsection
  
```
```
% datasette articles.db         --setting default_page_size 3000 \
        --setting max_returned_rows 3000 \
        --setting default_facet_size 3000 \
        --metadata metadata.json
        --template-dir templates/
```
