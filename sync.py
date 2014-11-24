from jira.client import JIRA
from jira.client import GreenHopper
import json

config = json.load(open("config.json"))

options = {
    'server': config['jira']['url']
}
jira = JIRA(options=options, basic_auth=(config['jira']['username'], config['jira']['password']))
gh = GreenHopper(options=options, basic_auth=(config['jira']['username'], config['jira']['password']))

boards = gh.boards()

for board in boards:
    sprints = gh.sprints(board.id)
    print board, sprints


issues = jira.search_issues('project=AH AND status != Closed', maxResults=False)
print len(issues)
