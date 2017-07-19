import yaml

with open('files2dirs.yaml') as yamlfile:
    config = yaml.load(yamlfile)

for section in config:
    print(section)

print(config['files2dirs']['agendazz'])
