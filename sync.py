from __future__ import unicode_literals
import github3
from jira.client import JIRA
from jira.client import GreenHopper
import json

config = json.load(open("config.json"))

options = {
    'server': config['jira']['url']
}
jira_prefix = config['jira']['prefix']
jira = JIRA(options=options, basic_auth=(config['jira']['username'], config['jira']['password']))
green = GreenHopper(options=options, basic_auth=(config['jira']['username'], config['jira']['password']))

boards = green.boards()

for board in boards:
    sprints = green.sprints(board.id)
    print board, sprints


jira_issues = jira.search_issues('project=AH AND status != Closed', maxResults=False)
jira_issues_by_key = dict((i.key, i) for i in jira_issues)

github = github3.login(config['github']['auth']['username'], config['github']['auth']['password'])
github_issues = [result.issue for result in github.search_issues("repo:activityhero/kidzexcel state:open")]

def jira_from_github_issue(ghissue):
    if ghissue.title.startswith(jira_prefix + '-'):
        key = ghissue.title.split(":")[0]
        return jira_issues_by_key.get(key)


def jira_to_github_author_tag(jira_user):
    github_user = config['userMapping'].get(jira_user)
    if github_user:
        return "@" + github_user
    else:
        return "jira: " + jira_user

def sync_bodies_from_jira():
    for ghissue in github_issues:
        if len(ghissue.body_html) == 0:
            jissue = jira_from_github_issue(ghissue)
            if jissue is not None:
                body = "%s/browse/%s" % (config['jira']['url'], jissue.key)
                body += "\nCreated by: %s" % jira_to_github_author_tag(jissue.fields.reporter.name)
                body += "\nReported on: %s" % jissue.fields.created
                if jissue.fields.description:
                    body += "\n\n" + jissue.fields.description.replace("\r\n", "\n")
                ghissue.edit(body=body)

def sync_comments_from_jira():
    for ghissue in github_issues:
        if ghissue.comments == 0:
            jissue = jira_from_github_issue(ghissue)
            if jissue is not None:
                jissue = jira.issue(jissue.key)
                if jissue.fields.comment:
                    for jcomment in jissue.fields.comment.comments:
                        body = "\nComment by: %s" % jira_to_github_author_tag(jcomment.author.name)
                        body += " on: %s" % jcomment.created
                        body += "\n\n" + jcomment.body.replace("\r\n", "\n")
                        print body
                        ghissue.create_comment(body)

#sync_bodies_from_jira()
sync_comments_from_jira()