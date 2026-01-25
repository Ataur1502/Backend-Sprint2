from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from django.core import mail
from .models import User, MFASession


class AdminMFAFlowTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='admin1', email='admin@test.com', password='pass123', role='COLLEGE_ADMIN')

    def test_admin_login_initiates_duo_push_and_verify(self):
        # Patch send_duo_push to simulate Duo queuing a push and returning an mfa_id
        from unittest.mock import patch
        with patch('custom_auth.views.send_duo_push') as mock_send_duo:
            # Simulate returning (success, message, mfa_id)
            mock_send_duo.return_value = (True, 'Duo push queued', '00000000-0000-0000-0000-000000000000')
            res = self.client.post('/auth/admin-login/', {'email': self.user.email, 'password': 'pass123'}, format='json')
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.data.get('mfa_required'))
            self.assertIn('mfa_id', res.data)

        # Now simulate the verify step: patch check_duo_status to return allow
        from unittest.mock import patch
        with patch('custom_auth.utils.check_duo_status') as mock_check:
            from .models import MFASession
            dummy_session = MFASession.objects.create(user=self.user, duo_txid='dummy-txid')
            mock_check.return_value = ('allow', 'approved', dummy_session)

            res2 = self.client.post('/auth/admin-verify-otp/', {'mfa_id': str(dummy_session.id)}, format='json')
            self.assertEqual(res2.status_code, 200)
            self.assertIn('access', res2.data)
            self.assertIn('refresh', res2.data)
            self.assertIn('mfa_id', res2.data)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_non_admin_role_cannot_request_mfa(self):
        # Even via admin-login URL, the unified view allows login but just doesn't trigger MFA
        user = User.objects.create_user(username='student1', email='student@test.com', password='s', role='STUDENT')
        res = self.client.post('/auth/admin-login/', {'email': user.email, 'password': 's'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)

    def test_lowercase_role_initiates_mfa(self):
        # Verify that 'college_admin' (lowercase) triggers MFA
        user = User.objects.create_user(username='cadmin', email='cadmin@test.com', password='p', role='college_admin')
        
        from unittest.mock import patch
        with patch('custom_auth.views.send_duo_push') as mock_send_duo:
            mock_send_duo.return_value = (True, 'Duo push queued', '11111111-1111-1111-1111-111111111111')
            res = self.client.post('/auth/api/login/', {'email': user.email, 'password': 'p'}, format='json')
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.data.get('mfa_required'))
            self.assertEqual(res.data.get('role'), 'college_admin')

    def test_non_mfa_role_gets_tokens(self):
        # FACULTY or STUDENT should get tokens directly from /login/
        faculty = User.objects.create_user(username='faculty1', email='faculty@test.com', password='fpass', role='FACULTY')
        res = self.client.post('/auth/api/login/', {'username': faculty.email, 'password': 'fpass'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)
        self.assertEqual(res.data['role'], 'FACULTY')

    def test_non_mfa_role_gets_tokens_form_encoded(self):
        # Verify form-encoded (application/x-www-form-urlencoded) posts are accepted
        faculty = User.objects.create_user(username='faculty2', email='faculty2@test.com', password='fpass2', role='FACULTY')
        # Use format='multipart' to simulate form submissions (APIClient supports this)
        res = self.client.post('/auth/api/login/', {'username': faculty.email, 'password': 'fpass2'}, format='multipart')
        self.assertEqual(res.status_code, 200)
        data = res.json() if hasattr(res, 'json') else res.data
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertEqual(data['role'], 'FACULTY')

    def test_duo_webhook_applies_allow(self):
        import json, hmac, hashlib
        from django.test import override_settings

        # Create an MFA session that represents an outstanding duo push
        sess = MFASession.objects.create(user=self.user, duo_txid='tx-1234', duo_status='pending')

        body = json.dumps({'txid': 'tx-1234', 'result': 'allow'}).encode('utf-8')
        secret = 's3cr3t'
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        # Post with correct signature
        with override_settings(DUO_WEBHOOK_SECRET=secret):
            res = self.client.post('/auth/api/duo/webhook/', data=body, content_type='application/json', HTTP_X_Duo_Signature=sig)
            self.assertEqual(res.status_code, 200)
            sess.refresh_from_db()
            self.assertEqual(sess.duo_status, 'allow')
            self.assertTrue(sess.is_verified)

    def test_duo_webhook_rejects_bad_signature(self):
        import json, hmac, hashlib
        from django.test import override_settings

        sess = MFASession.objects.create(user=self.user, duo_txid='tx-5678', duo_status='pending')
        body = json.dumps({'txid': 'tx-5678', 'result': 'deny'}).encode('utf-8')
        secret = 's3cr3t'
        bad_sig = 'bad-signature'

        with override_settings(DUO_WEBHOOK_SECRET=secret):
            res = self.client.post('/auth/api/duo/webhook/', data=body, content_type='application/json', HTTP_X_Duo_Signature=bad_sig)
            self.assertEqual(res.status_code, 403)
            sess.refresh_from_db()
            self.assertEqual(sess.duo_status, 'pending')

    def test_manage_command_duo_pending_lists_sessions(self):
        from django.core.management import call_command
        from io import StringIO

        # Create a pending session
        sess = MFASession.objects.create(user=self.user, duo_txid='tx-list-1', duo_status='pending')

        out = StringIO()
        call_command('duo_pending', stdout=out)
        output = out.getvalue()
        self.assertIn('Found 1 MFASession', output)
        self.assertIn('tx-list-1', output)

    def test_manage_command_duo_pending_poll_updates(self):
        from django.core.management import call_command
        from io import StringIO
        from unittest.mock import patch

        sess = MFASession.objects.create(user=self.user, duo_txid='tx-poll-1', duo_status='pending')

        # Mock check_du_status to simulate an allow and update DB
        def fake_check(mfa_id):
            sess.duo_status = 'allow'
            sess.is_verified = True
            sess.save()
            return ('allow', 'approved', sess)

        with patch('custom_auth.management.commands.duo_pending.check_duo_status') as mock_check:
            mock_check.side_effect = fake_check
            out = StringIO()
            call_command('duo_pending', '--poll', stdout=out)
            sess.refresh_from_db()
            self.assertEqual(sess.duo_status, 'allow')
            self.assertTrue(sess.is_verified)
            output = out.getvalue()
            self.assertIn('poll result', output)
