#!/usr/bin/env python3
"""Collecte d'offres via API publique Jobicy et flux RSS explicitement configurés."""
import json, os, re, hashlib, html, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
CONFIG=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
DATA_PATH=ROOT/'data'/'jobs.json'
NOW=datetime.now(timezone.utc)
KEYWORDS=[x.lower() for x in CONFIG.get('keywords',[])]
CASA=[x.lower() for x in CONFIG.get('casablanca_terms',[])]
REMOTE=[x.lower() for x in CONFIG.get('remote_terms',[])]

def clean(value):
    value=html.unescape(re.sub(r'<[^>]+>', ' ', str(value or '')))
    return re.sub(r'\s+', ' ', value).strip()

def parse_date(value):
    if not value:return None
    value=str(value).strip()
    try:
        d=datetime.fromisoformat(value.replace('Z','+00:00'))
        if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
    except ValueError:pass
    try:
        d=parsedate_to_datetime(value)
        if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
    except Exception:return None

def relevant(title, desc):
    text=(title+' '+desc).lower()
    return any(k in text for k in KEYWORDS)

def eligible_location(location, desc=''):
    loc=(location+' '+desc[:1500]).lower()
    casa=any(t in loc for t in CASA)
    remote=any(t in loc for t in REMOTE) or 'remote' in loc or 'télétravail' in loc
    # Remote jobs tied to a specific non-Moroccan country are not presumed accessible from Morocco.
    restricted=re.search(r'\b(usa only|us only|united states only|uk only|canada only|must be based in (the )?(us|usa|uk|canada))\b',loc)
    if restricted and not re.search(r'morocco|maroc|worldwide|anywhere',loc): remote=False
    morocco=any(t in loc for t in ['morocco','maroc','casablanca','rabat','marrakech','tanger','fes','agadir'])
    return casa or morocco or (remote and any(t in loc for t in ['anywhere','worldwide','morocco','maroc','africa','europe','emea','global','remote']))

def make_id(url,title,company):
    normalized=(url or '').strip().rstrip('/').lower()
    raw=normalized or (title.strip().lower()+'|'+company.strip().lower())
    return hashlib.sha256(raw.encode()).hexdigest()[:20]

def normalize(title, company, location, pub, url, description, source, remote=None):
    title,company,location,description=map(clean,[title,company,location,description])
    if not title or not url or not url.startswith(('https://','http://')):return None
    if not relevant(title,description) or not eligible_location(location,description):return None
    if remote is None:remote=any(t in (location+' '+description[:1000]).lower() for t in REMOTE) or 'remote' in (location+' '+description[:1000]).lower() or 'télétravail' in (location+' '+description[:1000]).lower()
    return {'id':make_id(url,title,company),'title':title,'company':company or 'Entreprise non précisée','location':location or 'Lieu non précisé','publishedAt':parse_date(pub),'detectedAt':NOW.isoformat().replace('+00:00','Z'),'url':url.strip(),'description':description[:1200],'source':source,'remote':bool(remote)}

def request_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':'VeilleEmploiCasablanca/1.0 (personal job search; respects source terms)','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=25) as response:return json.loads(response.read().decode('utf-8'))

def collect_jobicy():
    url='https://jobicy.com/api/v2/remote-jobs?'+urllib.parse.urlencode({'count':min(max(int(CONFIG.get('jobicy_count',200)),1),200)})
    payload=request_json(url);out=[]
    for item in payload.get('jobs',[]):
        title=clean(item.get('jobTitle'));desc=clean(item.get('jobExcerpt') or item.get('jobDescription'))
        location=clean(item.get('jobGeo') or 'Remote')
        # Public API entries are remote. Only include broad/global/regionally eligible locations.
        if not eligible_location(location,desc):continue
        j=normalize(title,item.get('companyName'),location,item.get('pubDate'),item.get('url'),desc,'Jobicy',True)
        if j:out.append(j)
    return out,len(payload.get('jobs',[]))

def rss_text(node, names):
    for name in names:
        el=node.find(name)
        if el is not None and el.text:return el.text.strip()
        # Atom namespace fallback
        for child in node:
            if child.tag.split('}')[-1]==name:
                if name=='link':return child.attrib.get('href','')
                if child.text:return child.text.strip()
    return ''

def collect_rss(feed):
    req=urllib.request.Request(feed['url'],headers={'User-Agent':'VeilleEmploiCasablanca/1.0 (RSS reader)','Accept':'application/rss+xml, application/atom+xml, application/xml, text/xml'})
    with urllib.request.urlopen(req,timeout=25) as response:root=ET.fromstring(response.read())
    out=[]
    for node in root.iter():
        if node.tag.split('}')[-1] not in ('item','entry'):continue
        title=rss_text(node,['title']);link=rss_text(node,['link','guid','id'])
        if link and not link.startswith('http'):
            link_el=next((x for x in node if x.tag.split('}')[-1]=='link'),None)
            link=link_el.attrib.get('href','') if link_el is not None else ''
        desc=rss_text(node,['description','summary','content','encoded']);company=feed.get('company','')
        location=feed.get('location','')
        pub=rss_text(node,['pubDate','published','updated','date'])
        j=normalize(title,company,location,pub,link,desc,feed.get('name','Flux RSS'))
        if j:out.append(j)
    return out

def main():
    old={}
    if DATA_PATH.exists():
        try:
            previous=json.loads(DATA_PATH.read_text(encoding='utf-8'))
            old={j['id']:j for j in previous.get('jobs',[]) if j.get('id') and not j.get('demo')}
        except Exception:pass
    errors=[];sources=[];incoming=[]
    if CONFIG.get('jobicy_enabled',True):
        try:
            found,total=collect_jobicy();incoming.extend(found);sources.append({'name':'Jobicy API','status':'OK','count':len(found),'checked':total})
        except Exception as e:
            errors.append({'source':'Jobicy API','error':str(e)[:250]});sources.append({'name':'Jobicy API','status':'Erreur','count':0})
    for feed in CONFIG.get('rss_feeds',[]):
        try:
            found=collect_rss(feed);incoming.extend(found);sources.append({'name':feed.get('name','Flux RSS'),'status':'OK','count':len(found)})
        except Exception as e:
            errors.append({'source':feed.get('name','Flux RSS'),'error':str(e)[:250]});sources.append({'name':feed.get('name','Flux RSS'),'status':'Erreur','count':0})
    # Preserve original detection date for listings seen before; deduplicate by normalized URL hash.
    for job in incoming:
        if job['id'] in old:job['detectedAt']=old[job['id']].get('detectedAt') or job['detectedAt']
        old[job['id']]=job
    cutoff=NOW-timedelta(days=120)
    kept=[]
    for job in old.values():
        d=parse_date(job.get('publishedAt')) or parse_date(job.get('detectedAt'))
        if d and datetime.fromisoformat(d.replace('Z','+00:00'))>=cutoff:kept.append(job)
    kept.sort(key=lambda j:j.get('publishedAt') or '',reverse=True)
    output={'lastRun':NOW.isoformat().replace('+00:00','Z'),'jobs':kept,'errors':errors,'sources':sources,'demoMode':False}
    DATA_PATH.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Collecte terminée: {len(incoming)} résultats trouvés, {len(kept)} conservés, {len(errors)} erreur(s).")
    if errors:print(json.dumps(errors,ensure_ascii=False))
if __name__=='__main__':main()
