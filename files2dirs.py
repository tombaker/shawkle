import yaml

with open('files2dirs.yaml') as yamlfile:
    config = yaml.load(yamlfile)

import pprint
pprint.pprint(config['files2dirs'])

print(config['files2dirs']['agendazz'])
