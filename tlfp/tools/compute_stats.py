import os, sys, glob

from .common import strip_text, compute_similarity_by_articles, open_json, print_json, \
    clean_text_for_diff, datize


def find_amendements(path):
    for amdts_file in glob.glob(os.path.join(path, '**/amendements_*'), recursive=True):
        amendements = open_json(amdts_file)
        for subject in amendements.get('sujets', {}).values():
            for amdt in subject.get('amendements', []):
                yield amdt


def read_text(step):
    articles = step['texte.json']['articles']
    texte = ''
    for art in articles:
        for key in sorted(art['alineas'].keys()):
            if art['alineas'][key] != '':
                texte += strip_text(art['alineas'][key])
    return texte


def read_articles(step):
    articles = step['texte.json']['articles']
    return {art['titre']: clean_text_for_diff([art['alineas'][al] for al in sorted(art['alineas'].keys())]) for art in articles}


def find_first_and_last_steps(dos):
    first_found = False
    for i, s in enumerate(dos['steps']):
        if s['debats_order'] is None or s.get('echec'):
            continue
        if s.get('step') != "depot":
            first_found = True
            last = i
        if not first_found and s.get('step') == "depot":
            first = i
    return first, last


def find_first_and_last_texts(dos):
    first, last = find_first_and_last_steps(dos)

    first_text = read_text(dos['steps'][first])
    first_arts = read_articles(dos['steps'][first])
    last_text = read_text(dos['steps'][last])
    last_arts = read_articles(dos['steps'][last])

    return first_text, first_arts, last_text, last_arts


def process(output_dir, dos):
    stats = {}

    intervs = open_json(os.path.join(output_dir, 'viz/interventions.json'))
    stats['total_mots'] = sum([
        sum(i['total_mots'] for i in step['divisions'].values())
            for step in intervs.values()
    ])

    stats["total_intervenants"] = len({orat for step in intervs.values() for orat in step['orateurs'].keys()})
    stats["total_interventions"] = sum({division['total_intervs'] for step in intervs.values() for division in step['divisions'].values()})

    stats['total_amendements'] \
        = stats['total_amendements'] \
        = stats["total_amendements_adoptes"] \
        = stats["total_amendements_parlementaire"] \
        = stats["total_amendements_parlementaire_adoptes"] \
        = stats["total_amendements_gouvernement"] \
        = stats["total_amendements_gouvernement_adoptes"] \
        = 0

    for amdt in find_amendements(output_dir):
        stats['total_amendements'] += 1
        if amdt["sort"] == "adopté":
            stats["total_amendements_adoptes"] += 1
            if amdt["groupe"] == "Gouvernement":
                stats["total_amendements_gouvernement_adoptes"] += 1
            else:
                stats["total_amendements_parlementaire_adoptes"] += 1

        if amdt["groupe"] == "Gouvernement":
            stats["total_amendements_gouvernement"] += 1
        else:
            stats["total_amendements_parlementaire"] += 1

    stats["echecs_procedure"] = len([step for step in dos['steps'] if step.get("echec")])

    if 'end' in dos:
        stats["total_days"] = (datize(dos["end"]) - datize(dos["beginning"])).days + 1

        first_text, first_arts, last_text, last_arts = find_first_and_last_texts(dos)

        stats["total_input_articles"] = len(first_arts)
        stats["total_output_articles"] = len(last_arts)
        stats["ratio_articles_growth"] = len(last_arts) / len(first_arts)

        stats["ratio_texte_modif"] = 1 - compute_similarity_by_articles(first_arts, last_arts)
        stats["input_text_length"] = len("\n".join(first_text))
        stats["output_text_length"] = len("\n".join(last_text))

    return stats


if __name__ == '__main__':
    print_json(process(sys.argv[1], open_json(sys.argv[2])))
