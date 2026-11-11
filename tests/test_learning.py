import json
import time
import unittest
from unittest.mock import patch
import learning
import server
import test_wsgi


class RubricTests(unittest.TestCase):
    def test_vague_answer_and_keyword_list_do_not_earn_points(self):
        self.assertEqual(learning.assess(2, 'Recognition is when you have a cue')['score'], 0)
        self.assertEqual(learning.assess(9, 'dendrites axon neurotransmitters')['score'], 0)
        self.assertEqual(learning.assess(9, 'Dendrites do not receive signals')['score'], 0)

    def test_meaningful_relationships_earn_points(self):
        result = learning.assess(2, 'Recall produces an answer without seeing it. Recognition identifies information encountered before.')
        self.assertEqual(result['score'], 1)
        self.assertTrue(result['needs_review'])
        self.assertEqual(len(result['hints']), 2)

    def test_spaced_comparison_uses_same_questions(self):
        now = time.time()
        def answer(id, score, created, qid=0):
            return dict(id=id, question_id=qid, created=created, score=score, confidence=3)
        attempts = [answer(1, 0, now - 4 * learning.DAY), answer(2, 1, now - 4 * learning.DAY + 100), answer(3, .5, now)]
        summary = learning.learning_summary(attempts, server.QUESTIONS, now)
        self.assertEqual(summary['change'], 50)
        self.assertEqual(summary['schedule'][0]['due'], now + 3 * learning.DAY)
        self.assertFalse(summary['schedule'][0]['overdue'])
        self.assertEqual(summary['calibration'][0]['kind'], 'Overconfident')
        self.assertIsNone(learning.learning_summary(attempts[:2], server.QUESTIONS, now)['change'])
        self.assertTrue(learning.learning_summary(attempts[:1], server.QUESTIONS, now)['schedule'][0]['overdue'])
        self.assertTrue(learning.learning_summary([], server.QUESTIONS, now)['inactive'])


class LearningAPITests(test_wsgi.WSGITests):
    def accounts(self):
        _, headers, _ = self.request('/api/register', {'name': 'Student', 'email': 'learner@example.com', 'password': 'student-password'})
        student = headers['Set-Cookie'].split(';')[0]
        _, headers, _ = self.request('/api/login', {'email': 'admin@admin.com', 'password': 'test-password-123'})
        return student, headers['Set-Cookie'].split(';')[0]

    def test_teacher_mark_is_authorized_audited_and_updates_priority(self):
        student, admin = self.accounts()
        _, _, answer = self.request('/api/answer', {'question_id': 2, 'answer': 'Recognition is when you have a cue', 'confidence': 3}, student)
        self.assertNotIn('points', answer)
        self.assertEqual(answer['score'], 0)
        review = {'id': answer['id'], 'revision': 0, 'matched': [True, True], 'note': 'Teacher confirmed both points in discussion.'}
        self.assertEqual(self.request('/api/teacher-review', review, student)[0], 403)
        self.assertEqual(self.request('/api/teacher-review', review)[0], 401)
        self.assertEqual(self.request('/api/review', review, student)[0], 403)
        self.assertEqual(self.request('/api/teacher-review', review, admin)[0], 200)
        self.assertEqual(self.request('/api/teacher-review', review, admin)[0], 409)
        result = self.request('/api/data', cookie=student)[2]
        self.assertEqual(result['attempts'][0]['score'], 1)
        self.assertEqual(result['attempts'][0]['needs_review'], 0)
        self.assertEqual(result['learning']['schedule'], [])
        with server.connect() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM marking_audit').fetchone()[0], 1)
        self.assertEqual(self.request('/api/admin', cookie=student)[0], 403)

    def test_existing_marks_survive_repeated_migrations(self):
        student, _ = self.accounts()
        self.request('/api/answer', {'question_id': 0, 'answer': '', 'confidence': 1}, student)
        with server.connect() as con:
            con.execute("UPDATE attempts SET marking_version='legacy',score=0.5,matched='[true,false,false]'")
        server.init()
        server.init()
        result = self.request('/api/data', cookie=student)[2]['attempts'][0]
        self.assertEqual(result['score'], .5)
        self.assertEqual(result['marking_version'], 'legacy')


if __name__ == '__main__':
    unittest.main()
