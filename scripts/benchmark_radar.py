"""Real radar corpus projection; quality metrics require separately reviewed labels."""
import argparse,json
from pathlib import Path
from src.research.reporting import atomic,dumps
from src.research.radar.pipeline import TechnicalFinding
from src.research.radar.contracts import RADARS


def benchmark(root,labels=None):
    cases={}
    for path in Path(root).glob('*/reports/*.json'):
        f=TechnicalFinding.model_validate_json(path.read_text())
        cases[f.id]={'id':f.id,'radar_id':f.radar_id,'language':f.references[0].language,'title':f.references[0].title,'source_ids':[r.id for r in f.references],'source_urls':[r.url for r in f.references],'classification':f.classification,'significance':f.significance,'event_id':f.event_id,'observed_at_utc':f.observed_at_utc,'label':None}
    if labels:
        if not labels.get('reviewer') or not labels.get('reviewed_at_utc') or set(labels.get('cases',{}))!=set(cases):raise ValueError('Complete reviewed labels required')
        from src.research.radar.contracts import utc
        utc(labels['reviewed_at_utc'])
        for key,label in labels['cases'].items():
            if set(label)!={'relevant','high_significance','new_development','evidence_supported','canonical_event'} or any(type(label[k]) is not bool for k in ('relevant','high_significance','new_development','evidence_supported')) or not isinstance(label['canonical_event'],str):raise ValueError('Invalid review label')
            cases[key]['label']=label
    groups=[]
    for radar in RADARS:
        for lang in ('en','de','fr','unknown'):
            subset=[c for c in cases.values() if c['radar_id']==radar and c['language']==lang]
            metrics={k:None for k in ('precision_at_10','high_significance_recall','duplicate_suppression','new_development_recall','cross_language_accuracy','evidence_support_rate','model_latency_ms','model_cost_per_accepted','missed_high_significance')}
            if labels and subset:
                top=sorted(subset,key=lambda c:(-c['significance'],c['id']))[:10]
                metrics['precision_at_10']=sum(c['label']['relevant'] for c in top)/len(top)
                positives=[c for c in subset if c['label']['high_significance']]
                accepted=[c for c in subset if c['classification']=='HIGH_SIGNAL']
                metrics['high_significance_recall']=sum(c['classification']=='HIGH_SIGNAL' for c in positives)/len(positives) if positives else None
                metrics['missed_high_significance']=sum(c['classification']!='HIGH_SIGNAL' for c in positives)
                metrics['evidence_support_rate']=sum(c['label']['evidence_supported'] for c in accepted)/len(accepted) if accepted else None
                developments=[c for c in subset if c['label']['new_development']]
                metrics['new_development_recall']=sum(c['classification'] not in ('REDUNDANT_COVERAGE','LOW_PRIORITY') for c in developments)/len(developments) if developments else None
                pairs=[(a,b) for i,a in enumerate(subset) for b in subset[i+1:] if a['label']['canonical_event']==b['label']['canonical_event']]
                metrics['duplicate_suppression']=sum(a['event_id']==b['event_id'] for a,b in pairs)/len(pairs) if pairs else None
                cross=[(a,b) for a in subset for b in cases.values() if a['radar_id']==b['radar_id'] and a['language']!=b['language'] and a['label']['canonical_event']==b['label']['canonical_event']]
                metrics['cross_language_accuracy']=sum(a['event_id']==b['event_id'] for a,b in cross)/len(cross) if cross else None
            groups.append({'radar_id':radar,'language':lang,'count':len(subset),'metrics':metrics})
    return {'schema_version':'1.0','reviewed_ground_truth':bool(labels),'live_inference_quality_certified':False,'cases':list(cases.values()),'groups':groups,'limitations':['No independently reviewed labels supplied.' if not labels else 'Reviewed label coverage applies only to this sample.','Latency and cost remain null until measured live inference is available.','Test fixtures do not count as real research or quality ground truth.']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--labels',type=Path);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    atomic(args.output,dumps(benchmark(args.root,json.loads(args.labels.read_text()) if args.labels else None)))
