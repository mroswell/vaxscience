# coding=utf-8
import sys
import json
from typing import List


def transform(data):
    demographic_list = set(["Humans", "Male", "Female", "Young Adult", "Middle Aged", "Adolescent", "Child", "Aged, 80 and over", "Aged", "Adult"])
    for row in data:
        if row["MeSH"]:
            mesh = set([item.strip() for item in row["MeSH"].split("; ")])
            demo = demographic_list & mesh
            # row['MeSH'] = list(mesh)
            row["MeSH"] = list(mesh - demo)
            row['Demographics'] = list(demo)
            row['Main_Topic'] = [item.replace('*', '').split('/', 1)[0] for item in mesh if '*' in item]

        if row["Affiliation"]:
           row["Affiliation"] = row["Affiliation"].split("; ")
        if row["Author(s)"]:
           row["Author(s)"] = row["Author(s)"].split("; ")
    # for row in d:
    #     if row["MeSH"] is not None:
    #
    #         for item in row["MeSH"]:
    #             if "*" in item:
    #                 # item_main = item.replace('\*', '')
    #                 # item_main = item.split("/")[0]
    #                 row.setdefault("Main_Topic", []).append(item)
    #             if item in demographic_list:
    #                 row["MeSH"].remove(item)
    #                 row.setdefault("Demographics", []).append(item)

        # yield d
    return data

if __name__ == "__main__":
    # Opening JSON file
    f = open('r19articles.json')

    data = json.load(f)
    print(json.dumps(transform(data)))
