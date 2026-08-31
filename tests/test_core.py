from job_aggregation_engine.core import Job, canonicalize_url, is_relevant

def test_indeed_jk_is_identity_but_tracking_removed():
 u=canonicalize_url('https://uk.indeed.com/viewjob?jk=abc123&utm_source=x&trackingId=y')
 assert u == 'https://uk.indeed.com/viewjob?jk=abc123'

def test_unrelated_mst_rejected_for_tax():
 j=Job('Multi-Systemic Therapy Team Supervisor','Council',None,False,'Children and family therapy', 'Finance & Accounting / Tax','fixture',.9,None,'Macclesfield','indeed','https://x/1',None)
 assert not is_relevant(j, ['Tax advisor'], 'Finance & Accounting / Tax')

def test_matching_title_accepted_without_fake_date():
 j=Job('Tax Advisor','Firm',None,False,'Tax compliance', 'Finance & Accounting / Tax','fixture',.9,None,'Manchester','reed_uk','https://x/2',None)
 assert is_relevant(j, ['Tax advisor'], 'Finance & Accounting / Tax')
 assert j.date_posted is None
