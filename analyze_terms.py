import fitz, re

doc = fitz.open('test_data/orion.pdf')
questions = [
    'When did Project Orion start?',
    'When did Project Orion start, when was it released to production, and how many engineers were on the final team?',
    'What is the final approved engineering budget for Project Orion?',
    'What is the CEO salary?',
    'What is the operational owner of Project Orion?',
    'What was the initial engineering budget, what is the final approved budget, and why did the budget change?'
]
STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'can', 'what', 'which', 'who', 'when',
    'where', 'why', 'how', 'this', 'that', 'these', 'those', 'am', 'i', 'you',
    'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'its',
    'their', 'our', 'my', 'your', 'about', 'document', 'pdf', 'tell', 'find',
    'show', 'give', 'does', 'state', 'page'
}

for q in questions:
    words = re.findall(r"\b[A-Za-z0-9_\'-]+\b", q)
    terms = [w.lower().strip("'- ") for w in words]
    terms = [t for t in terms if t and t not in STOPWORDS and len(t) > 2]
    term_hits = {}
    for t in dict.fromkeys(terms):
        hits = [i+1 for i in range(len(doc)) if t in doc[i].get_text().lower()]
        term_hits[t] = hits
    print(q)
    print("   hits:", term_hits)
