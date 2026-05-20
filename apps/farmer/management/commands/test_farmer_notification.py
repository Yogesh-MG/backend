"""
Management command to test farmer push notifications.

Usage:
    python manage.py test_farmer_notification <farmer_id> [--title "Test"] [--body "Hello"]
"""
from django.core.management.base import BaseCommand, CommandError
from apps.accounts.models import FarmerProfile
from apps.farmer.notifications import send_farmer_push_notification


class Command(BaseCommand):
    help = 'Send a test push notification to a farmer'

    def add_arguments(self, parser):
        parser.add_argument('farmer_id', type=int, help='ID of the farmer to notify')
        parser.add_argument(
            '--title',
            type=str,
            default='🌿 FreshOn Test',
            help='Notification title'
        )
        parser.add_argument(
            '--body',
            type=str,
            default='This is a test notification from FreshOn!',
            help='Notification body'
        )

    def handle(self, *args, **options):
        farmer_id = options['farmer_id']
        title = options['title']
        body = options['body']

        try:
            farmer = FarmerProfile.objects.get(id=farmer_id)
        except FarmerProfile.DoesNotExist:
            raise CommandError(f'Farmer with ID {farmer_id} does not exist')

        self.stdout.write(f'Sending notification to farmer: {farmer.user.get_full_name() or farmer.user.username}')
        self.stdout.write(f'  FCM Token: {farmer.fcm_token[:50] if farmer.fcm_token else "Not set"}...')
        self.stdout.write(f'  Title: {title}')
        self.stdout.write(f'  Body: {body}')
        
        success = send_farmer_push_notification(
            farmer,
            title=title,
            body=body,
            data={'type': 'test', 'farmer_id': str(farmer_id)}
        )

        if success:
            self.stdout.write(self.style.SUCCESS('Notification sent successfully!'))
        else:
            if not farmer.fcm_token:
                self.stdout.write(self.style.ERROR('Failed: Farmer has no FCM token registered'))
                self.stdout.write('  Ask the farmer to enable push notifications in the app.')
            else:
                self.stdout.write(self.style.ERROR('Failed to send notification'))
                self.stdout.write('  Check that firebase-admin is configured correctly.')
