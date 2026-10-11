#!/usr/bin/env python3
"""Sync SCNUAutoPtr global Project #7. Requires gh login or GH_TOKEN.

Only project membership and projection fields are written; source issues are read-only.
"""
import json
import os
import re
import subprocess
import sys
import time

def gql(query, variables=None):
    p = subprocess.run(['gh','api','graphql','--input','-'], input=json.dumps({'query':query,'variables':variables or {}}), text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError('GitHub API request failed; check App installation, permission scopes, and API availability')
    result = json.loads(p.stdout)
    if result.get('errors'):
        raise RuntimeError('GitHub returned GraphQL errors; refusing to print private API response data')
    return result['data']
query = '''query($cursor:String) { search(query:"org:SCNUAutoPtr is:issue is:open sort:created-asc",type:ISSUE,first:100,after:$cursor) { issueCount pageInfo { hasNextPage endCursor } nodes { ... on Issue { id number title body url state stateReason updatedAt assignees(first:30) { nodes { login } } labels(first:60) { nodes { name } } repository { name nameWithOwner isArchived id } parent { id number url title state } subIssues(first:100) { totalCount nodes { id number url title state } } blockedBy(first:100) { totalCount nodes { id number url title state } } blocking(first:100) { totalCount nodes { id number url title state } } } } } }'''

PROJECT={'id':'PVT_kwDOB7pqFc4Bmmnf','number':7,'url':'https://github.com/orgs/SCNUAutoPtr/projects/7'}; PID=PROJECT['id']
DETAIL='''id number title body url state stateReason updatedAt assignees(first:30){nodes{login}} labels(first:60){nodes{name}} repository{name nameWithOwner isArchived id} parent{id number url title state} subIssues(first:100){totalCount nodes{id number url title state}} blockedBy(first:100){totalCount nodes{id number url title state}} blocking(first:100){totalCount nodes{id number url title state}}'''
def batch(operations):
    # Mutations execute sequentially on the server. Batches remain small enough to retry safely.
    for offset in range(0,len(operations),15):
        group=operations[offset:offset+15]
        body=' '.join(f'm{n}:{name}(input:{input}){{{selection}}}' for n,(name,input,selection) in enumerate(group))
        for attempt in range(3):
            try:
                gql('mutation{'+body+'}')
                break
            except Exception:
                if attempt==2: raise
                time.sleep(2**attempt)
        print(f'{offset+len(group)}/{len(operations)} mutations',flush=True)
def q(v): return json.dumps(v,ensure_ascii=False)
def project_items():
    items=[]; cursor=None
    while True:
        p=gql('query($id:ID!,$cursor:String){node(id:$id){... on ProjectV2{items(first:100,after:$cursor){pageInfo{hasNextPage endCursor} nodes{id content{... on Issue{'+DETAIL+'}} fieldValues(first:40){nodes{... on ProjectV2ItemFieldTextValue{text field{... on ProjectV2FieldCommon{id}}} ... on ProjectV2ItemFieldSingleSelectValue{optionId field{... on ProjectV2FieldCommon{id}}}}}}}}}}',{'id':PID,'cursor':cursor})['node']['items']
        items+=p['nodes']
        if not p['pageInfo']['hasNextPage']: return items
        cursor=p['pageInfo']['endCursor']
if __name__=='__main__':
    issues=[]; cursor=None
    while True:
        page=gql(query,{'cursor':cursor})['search']
        if page['issueCount']>1000: raise RuntimeError('GitHub search exceeded 1000 issues; repository pagination is required before syncing')
        issues+=page['nodes']
        if not page['pageInfo']['hasNextPage']: break
        cursor=page['pageInfo']['endCursor']
    current=project_items(); known={i['content']['id'] for i in current if i['content']}
    missing=[i for i in issues if i['id'] not in known]
    print('Adding',len(missing),'missing issues',flush=True)
    batch([('addProjectV2ItemById','{projectId:'+q(PID)+',contentId:'+q(i['id'])+'}','item{id}') for i in missing])
    # Re-read includes any closed related sub-issues added by GitHub's built-in workflow.
    current=project_items()
    fields=gql('query($id:ID!){node(id:$id){... on ProjectV2{fields(first:60){nodes{... on ProjectV2FieldCommon{id name} ... on ProjectV2SingleSelectField{options{id name}}}}}}}',{'id':PID})['node']['fields']['nodes']
    fs={f['name']:f for f in fields}; opts={f['name']:{o['name']:o['id'] for o in f.get('options',[])} for f in fields}
    ops=[]
    for item in current:
        i=item['content']
        if not i or not i.get('url'): continue
        for relation in ('subIssues','blockedBy','blocking'):
            if i[relation]['totalCount']>len(i[relation]['nodes']): raise RuntimeError('Issue relationships exceed a page; refusing an incomplete projection')
        labels={l['name'] for l in i['labels']['nodes']}
        blockers=i['blockedBy']['nodes']; downstream=i['blocking']['nodes']
        refs=list(dict.fromkeys(re.findall(r'https://github\.com/SCNUAutoPtr/[\w.-]+/issues/\d+',i['body'] or '')))
        values={
            '结案类型':('singleSelectOptionId','未关闭' if i['state']=='OPEN' else ('不计划' if i['stateReason']=='NOT_PLANNED' else ('完成' if i['stateReason']=='COMPLETED' else '关闭原因未明确'))),
            '仓库范围':('singleSelectOptionId','归档仓库' if i['repository']['isArchived'] else '活跃仓库'),
            '分配情况':('singleSelectOptionId','已分配' if i['assignees']['nodes'] else '待分配'),
            '依赖情况':('singleSelectOptionId','被阻塞' if any(b['state']=='OPEN' for b in blockers) else ('依赖已解除' if blockers else '无原生依赖')),
            '阻塞方':('text','\n'.join(b['url']+(' （已关闭）' if b['state']=='CLOSED' else '') for b in blockers)),
            '阻塞下游':('text','\n'.join(b['url']+(' （已关闭）' if b['state']=='CLOSED' else '') for b in downstream)),
            '正文关联引用':('text','\n'.join(refs)),
            # Only an explicit execution label is evidence of work in progress.
            'Status':('singleSelectOptionId','Done' if i['state']=='CLOSED' else ('In Progress' if 'Status: In Progress' in labels else 'Todo')),
        }
        present={v['field']['id']:v.get('text',v.get('optionId')) for v in item['fieldValues']['nodes'] if v.get('field')}
        for name,(typ,val) in values.items():
            fid=fs[name]['id']
            if typ=='singleSelectOptionId': val=opts[name][val]
            if present.get(fid,'')==val: continue
            if val:
                inp='{projectId:'+q(PID)+',itemId:'+q(item['id'])+',fieldId:'+q(fid)+',value:{'+typ+':'+q(val)+'}}'
                ops.append(('updateProjectV2ItemFieldValue',inp,'projectV2Item{id}'))
            else:
                inp='{projectId:'+q(PID)+',itemId:'+q(item['id'])+',fieldId:'+q(fid)+'}'
                ops.append(('clearProjectV2ItemFieldValue',inp,'projectV2Item{id}'))
    print('Updating',len(ops),'changed fields',flush=True); batch(ops)
    after=project_items(); actual={i['content']['id'] for i in after if i['content']}; expected={i['id'] for i in issues}
    summary={'project':PROJECT['url'],'openIssues':len(issues),'items':len(after),'missing':list(expected-actual),'active':sum(not i['repository']['isArchived'] for i in issues),'archived':sum(i['repository']['isArchived'] for i in issues),'unassignedActive':sum(not i['repository']['isArchived'] and not i['assignees']['nodes'] for i in issues),'blockedActive':sum(not i['repository']['isArchived'] and any(b['state']=='OPEN' for b in i['blockedBy']['nodes']) for i in issues)}
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        print('Synchronization finished; membership verification '+('FAILED' if summary['missing'] else 'passed')+'. Private issue data remains in the private project.',flush=True)
    else:
        print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    if summary['missing']: sys.exit(1)
