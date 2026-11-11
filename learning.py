"""Versioned, conservative rubric checks and spaced-practice evidence."""
import json
import re
import time

DAY = 86400
RETEST_DAYS = 3
# Each point requires a subject and a meaningful relationship in the same clause.
# These are original practice rubrics, not exam-board mark schemes.
RULES = [
    [(['sensory'], ['brief', 'short', 'sensory information', 'sensory input']), (['short term', 'stm'], ['limited', 'capacity', 'duration', 'brief']), (['long term', 'ltm'], ['extended', 'long time', 'permanent', 'unlimited', 'long duration'])],
    [(['executive', 'it'], ['attention', 'focus']), (['executive', 'it'], ['coordinates', 'coordinate', 'allocates', 'allocate', 'controls', 'control'])],
    [(['recall'], ['without', 'no cue', 'no prompt', 'generate', 'produce']), (['recognition'], ['identif', 'recognis', 'recogniz'], ['previous', 'before', 'familiar', 'encounter'])],
    [(['normative'], ['accept', 'reject', 'fit in', 'liked']), (['informational'], ['correct', 'right answer', 'accurate'])],
    [(['obedience'], ['instruction', 'order', 'command'], ['authority', 'authoritative']), (['conformity'], ['group', 'peer', 'norm'], ['adapt', 'change', 'pressure', 'follow', 'match'])],
    [(['consisten', 'minority', 'they'], ['time', 'same view', 'stable', 'agree', 'members']), (['consisten', 'minority', 'it', 'they'], ['reconsider', 'reflect', 'question', 'think'])],
    [(['infant', 'baby', 'child', 'proximity'], ['close', 'near', 'proximity seeking']), (['separat', 'leaves', 'leave'], ['distress', 'upset', 'cry'])],
    [(['model', 'it'], ['mental', 'expectation', 'representation'], ['relationship', 'attachment']), (['develop', 'form', 'based', 'shape'], ['early', 'caregiver', 'parent']), (['influenc', 'affect', 'shape'], ['later', 'future'], ['relationship'])],
    [(['cultur'], ['differ', 'interpret', 'vary', 'variation']), (['sample', 'participant'], ['limited', 'small', 'unrepresentative', 'representative', 'generalis', 'generaliz'])],
    [(['dendrit'], ['receiv']), (['axon'], ['carries', 'carry', 'transmit'], ['away', 'from the cell']), (['terminal', 'button'], ['release'], ['neurotransmit'])],
    [(['neurotransmit'], ['release'], ['presynaptic', 'pre synaptic', 'vesicle', 'terminal']), (['diffus'], ['gap', 'cleft', 'synapse']), (['bind', 'attach'], ['receptor'], ['postsynaptic', 'post synaptic', 'receiving'])],
    [(['central', 'cns'], ['brain'], ['spinal']), (['peripheral', 'pns'], ['connect', 'outside', 'rest of the body'])],
    [(['independent', 'iv'], ['manipulat', 'changed', 'changes']), (['dependent', 'dv'], ['measur', 'outcome'])],
    [(['reliability', 'reliable'], ['consisten', 'repeat']), (['validity', 'valid'], ['intended', 'intends', 'supposed', 'accurate'])],
    [(['consent'], ['information', 'informed'], ['agree', 'voluntar', 'permission']), (['withdraw', 'leave'], ['without penalty', 'no penalty', 'any time', 'anytime'])],
]
HINTS = [
    ['How briefly does the sensory store hold incoming information?', 'What limits apply to short-term storage?', 'How long can long-term storage last?'],
    ['What does the central executive direct?', 'How does it manage the other components?'],
    ['Does recall require the target answer to be shown?', 'What must someone identify in a recognition task, and have they encountered it before?'],
    ['What social outcome is someone seeking through normative influence?', 'Why might someone trust the group’s judgement?'],
    ['Who gives an instruction in obedience?', 'What pressure changes behaviour in conformity?'],
    ['How should the minority’s position relate across people and time?', 'What might a consistent minority make the majority do?'],
    ['Where might an infant try to stay?', 'What might happen when a caregiver leaves?'],
    ['What does this model represent?', 'Which early experiences shape it?', 'Which later experiences might it influence?'],
    ['Could the same behaviour have different meanings across cultures?', 'Who was sampled, and who might they fail to represent?'],
    ['What do dendrites do with incoming signals?', 'In which direction does an axon carry an impulse?', 'What is released at terminal buttons?'],
    ['What is released, and from which side of the synapse?', 'How does the chemical travel between neurons?', 'Where does it bind on the receiving cell?'],
    ['Which two structures make up the CNS?', 'What does the PNS connect?'],
    ['Which variable does the researcher change?', 'Which variable is recorded as the outcome?'],
    ['What would repeated measurements tell you about reliability?', 'Is the measure capturing what it was designed to capture?'],
    ['What information and choice are needed for consent?', 'Can a participant leave, and with what consequences?'],
]


def assess(question_id, answer):
    normal = re.sub(r'[-–]', ' ', answer.lower()).replace('’', "'")
    clauses = re.split(r'[.;!?\n]+|\bbut\b|\bwhereas\b', normal)
    negation = r"\b(?:not|never|isn't|doesn't|don't|cannot|can't)\b"
    matched = []
    evidence = []
    for groups in RULES[question_id]:
        supporting = next((c.strip() for c in clauses if all(any(re.search(r'\b' + re.escape(term), c) for term in group) for group in groups)
                           and not re.search(negation, c)), '')
        matched.append(bool(supporting))
        evidence.append(supporting)
    # Rule-based interpretation always remains subject to teacher judgement.
    return {'matched': matched, 'evidence': evidence, 'score': sum(matched) / len(matched),
            'hints': HINTS[question_id], 'needs_review': bool(answer.strip()), 'marking_version': 'rubric-v2'}


def migrate(con):
    columns = {r['name'] for r in con.execute('PRAGMA table_info(attempts)')}
    additions = {'marking_version': "TEXT NOT NULL DEFAULT 'legacy'", 'needs_review': 'INTEGER NOT NULL DEFAULT 1',
                 'evidence': "TEXT NOT NULL DEFAULT '[]'", 'teacher_note': "TEXT NOT NULL DEFAULT ''",
                 'teacher_id': 'INTEGER', 'marked_at': 'REAL', 'revision': 'INTEGER NOT NULL DEFAULT 0'}
    for name, declaration in additions.items():
        if name not in columns:
            con.execute(f'ALTER TABLE attempts ADD COLUMN {name} {declaration}')
    con.execute('''CREATE TABLE IF NOT EXISTS marking_audit(
        id INTEGER PRIMARY KEY, attempt_id INTEGER NOT NULL REFERENCES attempts(id),
        teacher_id INTEGER NOT NULL REFERENCES users(id), old_matched TEXT NOT NULL,
        new_matched TEXT NOT NULL, note TEXT NOT NULL, created REAL NOT NULL)''')


def learning_summary(attempts, questions, now=None):
    now = time.time() if now is None else now
    ordered = sorted(attempts, key=lambda a: (a['created'], a['id']))
    by_question = {}
    for a in ordered:
        by_question.setdefault(a['question_id'], []).append(a)
    schedule, calibration, comparisons = [], [], []
    for qid, history in by_question.items():
        first, last = history[0], history[-1]
        q = questions[qid]
        if last['score'] < .8:
            due = last['created'] + RETEST_DAYS * DAY
            schedule.append({'question_id': qid, 'topic': q[0], 'subtopic': q[1], 'due': due,
                             'overdue': due <= now, 'score': last['score']})
        expected = {1: .25, 2: .6, 3: .9}[last['confidence']]
        gap = expected - last['score']
        if abs(gap) >= .3:
            calibration.append({'question_id': qid, 'subtopic': q[1], 'confidence': last['confidence'],
                                'score': last['score'], 'kind': 'Overconfident' if gap > 0 else 'Underconfident',
                                'provisional': last.get('teacher_id') is None})
        spaced = [a for a in history[1:] if a['created'] - first['created'] >= RETEST_DAYS * DAY]
        if spaced:
            final = spaced[-1]
            comparisons.append({'question_id': qid, 'subtopic': q[1], 'first': first['score'],
                                'latest': final['score'], 'change': round((final['score'] - first['score']) * 100),
                                'provisional': first.get('teacher_id') is None or final.get('teacher_id') is None})
    schedule.sort(key=lambda x: (not x['overdue'], x['score'], x['due']))
    last_active = ordered[-1]['created'] if ordered else None
    return {'schedule': schedule, 'calibration': calibration, 'comparisons': comparisons,
            'change': round(sum(c['change'] for c in comparisons) / len(comparisons)) if comparisons else None,
            'inactive': last_active is None or now - last_active >= 7 * DAY,
            'last_active': last_active, 'retest_days': RETEST_DAYS}
