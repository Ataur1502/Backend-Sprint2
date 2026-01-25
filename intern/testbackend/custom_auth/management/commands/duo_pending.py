from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from custom_auth.models import MFASession
from custom_auth.utils import check_duo_status

class Command(BaseCommand):
    help = 'List pending Duo MFASessions and optionally poll Duo for their status.'

    def add_arguments(self, parser):
        parser.add_argument('--poll', action='store_true', help='Poll Duo for each pending session and update status')
        parser.add_argument('--limit', type=int, default=50, help='Limit number of sessions to list')
        parser.add_argument('--status', type=str, default='pending', help='Filter by Duo status (default: pending)')

    def handle(self, *args, **options):
        poll = options['poll']
        limit = options['limit']
        status = options['status']

        qs = MFASession.objects.filter(duo_txid__isnull=False, duo_status=status).order_by('created_at')[:limit]
        count = qs.count()
        self.stdout.write(self.style.SUCCESS(f'Found {count} MFASession(s) with duo_status="{status}" (showing up to {limit})'))

        for s in qs:
            expires = s.expires_at.isoformat() if s.expires_at else 'N/A'
            self.stdout.write(f'- id={s.id} user={s.user.email} txid={s.duo_txid} status={s.duo_status} created={s.created_at.isoformat()} expires={expires}')
            if poll:
                try:
                    st, msg, session = check_duo_status(s.id)
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'  Poll error for {s.id}: {e}'))
                    continue
                # Refresh from DB to get updated fields if any
                session.refresh_from_db()
                self.stdout.write(self.style.NOTICE(f'  -> poll result: {st} ({msg}) updated_status={session.duo_status} is_verified={session.is_verified}'))

        self.stdout.write(self.style.SUCCESS('Done.'))
