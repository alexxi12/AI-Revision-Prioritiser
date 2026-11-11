import json
import ai_workflow
import server
import test_learning


class AIWorkflowTests(test_learning.LearningAPITests):
    def prepare(self):
        student, admin = self.accounts()
        _, _, answer = self.request('/api/answer', {'question_id': 0, 'answer': 'Sensory memory holds incoming information briefly.', 'confidence': 2}, student)
        aid = answer['id']
        status, _, payload = self.request('/api/ai-prompt', {'id': aid, 'revision': 0}, admin)
        self.assertEqual(status, 200)
        prompt = payload['prompt']
        self.assertNotIn('learner@example.com', prompt)
        self.assertNotIn('student-password', prompt)
        self.assertIn('AQA', prompt)
        with server.connect() as con:
            row = con.execute('SELECT * FROM attempts WHERE id=?', (aid,)).fetchone()
            reference = ai_workflow.reference(row)
        suggestion = {'assessment_ref': reference, 'summary': 'One point demonstrated; revisit the other stores.', 'points': [
            {'id': i+1, 'met': i == 0, 'evidence': 'holds incoming information briefly' if i == 0 else '',
             'reason': 'Point demonstrated.' if i == 0 else 'Missing detail.',
             'hint': 'How long can this store retain information?', 'confidence': 'medium'}
            for i in range(3)]}
        return student, admin, aid, suggestion

    def test_import_does_not_mark_until_teacher_approval(self):
        student, admin, aid, suggestion = self.prepare()
        before = self.request('/api/data', cookie=student)[2]['attempts'][0]['score']
        payload = {'id': aid, 'revision': 0, 'provider': 'Test fixture (no live AI)', 'response': json.dumps(suggestion)}
        self.assertEqual(self.request('/api/ai-import', payload, student)[0], 403)
        self.assertEqual(self.request('/api/ai-import', payload)[0], 401)
        self.assertEqual(self.request('/api/ai-import', payload, admin)[0], 200)
        attempt = self.request('/api/data', cookie=student)[2]['attempts'][0]
        self.assertEqual(attempt['score'], before)
        self.assertEqual(attempt['ai_assessment'], '')
        self.assertNotIn('ai_ref', attempt)
        review = {'id': aid, 'revision': 1, 'matched': [True, False, False], 'note': 'Review the capacity and duration of the other stores.'}
        self.assertEqual(self.request('/api/teacher-review', review, admin)[0], 400)
        review['ai_confirmed'] = True
        self.assertEqual(self.request('/api/teacher-review', review, admin)[0], 200)
        attempt = self.request('/api/data', cookie=student)[2]['attempts'][0]
        self.assertEqual(attempt['ai_approved'], 1)
        self.assertEqual(attempt['score'], 1/3)
        self.assertEqual(json.loads(attempt['ai_assessment'])['summary'], suggestion['summary'])
        with server.connect() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM ai_imports').fetchone()[0], 1)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM marking_audit').fetchone()[0], 1)
        self.assertEqual(self.request('/api/ai-import', payload, admin)[0], 409)

    def test_bad_response_and_wrong_reference_are_rejected(self):
        student, admin, aid, suggestion = self.prepare()
        payload = {'id': aid, 'revision': 0, 'provider': 'Test fixture', 'response': '{}'}
        self.assertEqual(self.request('/api/ai-import', payload, admin)[0], 400)
        suggestion['assessment_ref'] = 'wrong-answer'
        payload['response'] = json.dumps(suggestion)
        self.assertEqual(self.request('/api/ai-import', payload, admin)[0], 400)
        self.assertEqual(self.request('/api/ai-prompt', {'id': aid, 'revision': 0}, student)[0], 403)

    def test_invented_quotes_and_missing_points_are_rejected(self):
        _, admin, aid, suggestion = self.prepare()
        payload = {'id': aid, 'revision': 0, 'provider': 'Test fixture'}
        suggestion['points'][0]['evidence'] = 'This was never in the answer'
        payload['response'] = json.dumps(suggestion)
        self.assertEqual(self.request('/api/ai-import', payload, admin)[0], 400)
        suggestion['points'].pop()
        payload['response'] = json.dumps(suggestion)
        self.assertEqual(self.request('/api/ai-import', payload, admin)[0], 400)

    def test_fenced_json_and_source_metadata(self):
        student, admin, aid, suggestion = self.prepare()
        payload = {'id': aid, 'revision': 0, 'provider': 'Test fixture', 'response': '```json\n'+json.dumps(suggestion)+'\n```'}
        self.assertEqual(self.request('/api/ai-import', payload, admin)[0], 200)
        source = self.request('/api/data', cookie=student)[2]['questions'][0]['source']
        self.assertIn('aqa.org.uk', source['url'])
        self.assertIn('Original practice', source['alignment'])
