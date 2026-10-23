"""Read-only audit of funding folders, history, local navigation and nominations."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from src.research.funding.models import Applicant, Opportunity, assess
from src.research.funding.storage import folder_name
from src.research.profiles import ROOT
from src.research.reporting import dumps


def audit(root=ROOT):
    root=Path(root);base=root/'research/funding-de-eu'
    applicant=Applicant.model_validate_json((root/'config/funding-applicant.json').read_text())
    index=json.loads((base/'index.json').read_text());ids=set();counts=Counter();links=0
    markdown=[root/'Funding DK (DE missing).md']+[base/n for n in ('README.md','ACTIVE_OPPORTUNITIES.md','REVIEW_REQUIRED.md','ARCHIVED_OPPORTUNITIES.md')]
    required=['opportunity.json','eligibility.md','benefits-and-costs.md','application-guide.md','required-documents.md','evidence.md','sources.json','change-history.jsonl','resources/README.md','resources/links.json']
    for row in index['opportunities']:
        record_path=base/row['record'];record=Opportunity.model_validate_json(record_path.read_text());folder=record_path.parent
        if record.opportunity_id in ids or folder.name!=folder_name(record):raise ValueError('Duplicate ID or incorrect deadline folder')
        ids.add(record.opportunity_id);result=assess(record,applicant);counts[result['status']]+=1
        expected='00_OVERVIEW__'+result['status']+'__'+record.deadline_token+'.md'
        if row['opportunity_id']!=record.opportunity_id or row['eligibility_status']!=result['status'] or row['deadline']!=record.deadline_token or Path(row['overview']).name!=expected:raise ValueError('Index status, ID or deadline mismatch')
        if sorted(p.name for p in folder.glob('00_OVERVIEW__*.md'))!=[expected]:raise ValueError('Missing/duplicate/misnamed overview')
        if any(not (folder/p).is_file() for p in required):raise ValueError('Incomplete opportunity folder')
        if not (base/row['overview']).is_file():raise ValueError('Broken index overview')
        events=[json.loads(line) for line in (folder/'change-history.jsonl').read_text().splitlines()]
        digests=[]
        for event in events:
            old=Opportunity.model_validate(event['record'])
            digest=hashlib.sha256(dumps(event['record']).encode()).hexdigest()
            if old.opportunity_id!=record.opportunity_id or event['opportunity_id']!=record.opportunity_id or event['record_sha256']!=digest:raise ValueError('Invalid immutable history')
            digests.append(digest)
        if len(set(digests))!=len(digests) or digests[-1]!=hashlib.sha256(dumps(record.model_dump(mode='json')).encode()).hexdigest():raise ValueError('Duplicate or stale history event')
        markdown+=list(folder.glob('*.md'))+list((folder/'resources').glob('*.md'))
    for path in markdown:
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text()):
            if urlsplit(target).scheme or target.startswith('#'):continue
            dest=(path.parent/unquote(target.split('#')[0])).resolve()
            if not dest.is_relative_to(root.resolve()) or not dest.is_file():raise ValueError('Broken or escaped local link: '+str(path.relative_to(root)))
            links+=1
    queue=json.loads((base/'RESEARCH_QUEUE.json').read_text())
    candidates={c['candidate_id'] for c in queue['candidates'] if c['origin']=='public_search'}
    reviews=json.loads((base/'NOMINATION_REVIEWS.json').read_text())
    reviewed={r['candidate_id'] for r in reviews['reviews']}
    if len(reviewed)!=len(reviews['reviews']):raise ValueError('Duplicate nomination qualification')
    for r in reviews['reviews']:
        if r['review_status']=='pending' and (r['verified_distinct_opportunity'] or r['eligibility_status']!='ELIGIBILITY_UNKNOWN'):raise ValueError('Unverified nomination promoted')
    nomination_counts=Counter(r['review_status'] for r in reviews['reviews'] if r['candidate_id'] in candidates)
    nomination_counts['pending']+=len(candidates-reviewed)
    return {'opportunities':len(ids),'eligibility_counts':dict(counts),'local_links_checked':links,'nomination_counts':dict(nomination_counts),'new_pending_nominations':len(candidates-reviewed),'seed_sha256':hashlib.sha256((base/'Funding DK (DE missing).md').read_bytes()).hexdigest()}


if __name__=='__main__':print(json.dumps(audit(),indent=2))
