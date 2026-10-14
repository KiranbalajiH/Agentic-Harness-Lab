import re

q = "What was the founding year of the company?"
q_lower = q.lower()
STOPWORDS = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'what', 'which', 'who', 'when', 'where', 'why', 'how', 'this', 'that', 'these', 'those', 'am', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'its', 'their', 'our', 'my', 'your', 'about', 'document', 'pdf', 'tell', 'find', 'show', 'give', 'state', 'page', 'much', 'many'}

q_words = set(re.findall(r"\b[A-Za-z0-9_\'-]+\b", q_lower)) - STOPWORDS
print('q_words:', q_words)

stmts = [
    'The primary color of the company logo is deep blue. The company was founded in 1995.',
    "Project 'Alpha' was completed in December of the same year with 15 engineers."
]

for stmt in stmts:
    s_lower = stmt.lower()
    score = sum(1 for w in q_words if w in s_lower)
    print(f'Stmt: {stmt[:50]}... -> score={score}')
