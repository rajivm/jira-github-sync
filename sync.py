from __future__ import unicode_literals
import github3
from jira.client import JIRA
from jira.client import GreenHopper
import json
from collections import defaultdict

config = json.load(open("config.json"))

options = {
    'server': config['jira']['url']
}
jira_prefix = config['jira']['prefix']
jira = JIRA(options=options, basic_auth=(config['jira']['username'], config['jira']['password']))
green = GreenHopper(options=options, basic_auth=(config['jira']['username'], config['jira']['password']))

# boards = green.boards()

# for board in boards:
#     sprints = green.sprints(board.id)
#     print board, sprints


jira_issues = jira.search_issues('project=AH AND status != Closed', maxResults=False)
jira_issues_by_key = dict((i.key, i) for i in jira_issues)

github = github3.login(config['github']['auth']['username'], config['github']['auth']['password'])
github_issues = [result.issue for result in github.search_issues("repo:activityhero/kidzexcel state:open")]
github_issues_by_jira_key = {}
for ghissue in github_issues:
    if ghissue.title.startswith(jira_prefix + '-'):
        key = ghissue.title.split(":")[0]
        github_issues_by_jira_key[key] = ghissue


def jira_from_github_issue(ghissue):
    if ghissue.title.startswith(jira_prefix + '-'):
        key = ghissue.title.split(":")[0]
        return jira_issues_by_key.get(key)


def github_from_jira_issue(jissue):
    github_issues_by_jira_key.get(jissue.key)


def jira_to_github_author_tag(jira_user):
    github_user = config['userMapping'].get(jira_user)
    if github_user:
        return "@" + github_user
    else:
        return "jira: " + jira_user


def body_from_jira_issue(jissue):
    body = "%s/browse/%s" % (config['jira']['url'], jissue.key)
    body += "\nCreated by: %s" % jira_to_github_author_tag(jissue.fields.reporter.name)
    body += "\nReported on: %s" % jissue.fields.created
    if jissue.fields.description:
        body += "\n\n" + jissue.fields.description.replace("\r\n", "\n")
    return body


def sync_issues():
    for jissue in jira_issues:
        ghissue = github_from_jira_issue(jissue)
        if not ghissue:
            title = "%s: %s" % (jissue.key, jissue.fields.summary)
            labels = []
            if jissue.fields.issuetype:
                labels.append(jissue.fields.issuetype.name)
            if jissue.fields.priority:
                labels.append(jissue.fields.priority.name)
            for c in jissue.fields.components:
                labels.append(c.name)
            for l in jissue.fields.labels:
                labels.append(l)
            body = body_from_jira_issue(jissue)
            assignee = None
            if jissue.fields.assignee:
                assignee = config['userMapping'].get(jissue.fields.assignee.name)
            kwargs = {
                'labels': labels,
                'body': body,
                'assignee': assignee,
                'title': title,
            }
            print "creating", kwargs
            github.create_issue(config['github']['user'], config['github']['repo'], **kwargs)


def sync_bodies_from_jira():
    for ghissue in github_issues:
        if len(ghissue.body_html) == 0:
            jissue = jira_from_github_issue(ghissue)
            if jissue is not None:
                body = body_from_jira_issue(jissue)
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


def remove_github_duplicates():
    issue_by_title = defaultdict(list)
    for ghissue in github_issues:
        issue_by_title[ghissue.title].append(ghissue)

    for title, issue_list in issue_by_title.iteritems():
        if (len(issue_list) > 1):
            to_delete = issue_list[1:]
            for dissue in to_delete:
                dissue.edit(title='-', state='closed')


#remove_github_duplicates()
#sync_issues()
#sync_bodies_from_jira()
#sync_comments_from_jira()
