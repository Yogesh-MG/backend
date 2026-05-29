"""
Django management command to sync attendance data from Petpooja Payroll API.

Usage:
    python manage.py sync_attendance
    python manage.py sync_attendance --date=2025-09-01
    python manage.py sync_attendance --start-date=2025-09-01 --end-date=2025-09-07
    python manage.py sync_attendance --dry-run

Scheduling:
    This command can be scheduled via cron or Celery beat:
    - Daily at midnight: 0 0 * * * /path/to/python /path/to/manage.py sync_attendance
    - Hourly: 0 * * * * /path/to/python /path/to/manage.py sync_attendance
"""

import logging
from datetime import date, timedelta
from typing import List, Dict, Any
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Employee, AttendancePunch
from apps.accounts.petpooja_client import get_petpooja_client, PetpoojaAPIError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync attendance punch data from Petpooja Payroll API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Sync attendance for a specific date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for date range (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for date range (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes'
        )
        parser.add_argument(
            '--emp-id',
            type=str,
            help='Sync only for a specific employee ID'
        )

    def handle(self, *args, **options):
        # Parse dates
        sync_date = options.get('date')
        start_date_str = options.get('start_date')
        end_date_str = options.get('end_date')
        dry_run = options.get('dry_run', False)
        specific_emp_id = options.get('emp_id')
        
        if sync_date:
            try:
                start_date = date.fromisoformat(sync_date)
                end_date = start_date
            except ValueError:
                raise CommandError(f"Invalid date format: {sync_date}. Use YYYY-MM-DD.")
        elif start_date_str and end_date_str:
            try:
                start_date = date.fromisoformat(start_date_str)
                end_date = date.fromisoformat(end_date_str)
            except ValueError:
                raise CommandError("Invalid date format. Use YYYY-MM-DD.")
        else:
            # Default: sync yesterday's data
            yesterday = date.today() - timedelta(days=1)
            start_date = yesterday
            end_date = yesterday
        
        if start_date > end_date:
            raise CommandError("Start date must be before or equal to end date")
        
        self.stdout.write(
            self.style.NOTICE(
                f"Syncing attendance from {start_date} to {end_date}"
                f"{' (DRY RUN)' if dry_run else ''}"
            )
        )
        
        try:
            # Get Petpooja client
            client = get_petpooja_client()
            
            # Fetch punch data from API
            punch_data = client.fetch_daily_punches(start_date, end_date)
            
            if not punch_data:
                self.stdout.write(self.style.WARNING("No punch data found for the specified date range"))
                return
            
            # Process and store punch data
            stats = self._process_punch_data(
                punch_data, 
                start_date, 
                end_date,
                specific_emp_id,
                dry_run
            )
            
            # Print summary
            self._print_summary(stats, dry_run)
            
        except PetpoojaAPIError as e:
            logger.error(f"Petpooja API error: {e}")
            raise CommandError(f"Failed to sync attendance: {e}")
        except Exception as e:
            logger.exception("Unexpected error during attendance sync")
            raise CommandError(f"Unexpected error: {e}")
    
    def _process_punch_data(
        self, 
        punch_data: List[Dict[str, Any]], 
        start_date: date,
        end_date: date,
        specific_emp_id: str = None,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Process punch data and create AttendancePunch records.
        
        Args:
            punch_data: Raw punch data from API
            start_date: Start date of sync range
            end_date: End date of sync range
            specific_emp_id: If provided, only process this employee
            dry_run: If True, don't actually create records
        
        Returns:
            dict: Statistics about the sync operation
        """
        stats = {
            'employees_found': 0,
            'employees_not_found': 0,
            'punches_created': 0,
            'punches_skipped': 0,
            'errors': 0
        }
        
        # Build a lookup of employees by emp_id
        employee_lookup = {
            emp.emp_id: emp 
            for emp in Employee.objects.filter(is_active=True)
        }
        
        for employee_record in punch_data:
            emp_id = employee_record.get('emp_id')
            
            # Skip if we're looking for a specific employee
            if specific_emp_id and emp_id != specific_emp_id:
                continue
            
            # Find the employee in our database
            employee = employee_lookup.get(emp_id)
            
            if not employee:
                self.stdout.write(
                    self.style.WARNING(f"Employee not found: {emp_id}")
                )
                stats['employees_not_found'] += 1
                continue
            
            stats['employees_found'] += 1
            
            # Process punch data for this employee
            payroll_date_str = employee_record.get('payroll_date')
            punch_list = employee_record.get('punch_data', [])
            
            try:
                payroll_date = date.fromisoformat(payroll_date_str) if payroll_date_str else start_date
            except ValueError:
                payroll_date = start_date
            
            for punch in punch_list:
                operation = punch.get('operation')  # "In" or "Out"
                time_str = punch.get('time')  # "HH:MM:SS"
                
                if not operation or not time_str:
                    stats['errors'] += 1
                    continue
                
                # Parse punch time
                try:
                    from datetime import datetime
                    punch_datetime = datetime.strptime(
                        f"{payroll_date} {time_str}",
                        "%Y-%m-%d %H:%M:%S"
                    )
                    # Make timezone aware
                    punch_datetime = timezone.make_aware(punch_datetime)
                except ValueError as e:
                    self.stdout.write(
                        self.style.ERROR(f"Invalid time format for {emp_id}: {time_str}")
                    )
                    stats['errors'] += 1
                    continue
                
                # Check if punch already exists
                exists = AttendancePunch.objects.filter(
                    employee=employee,
                    punch_time=punch_datetime,
                    operation=operation
                ).exists()
                
                if exists:
                    stats['punches_skipped'] += 1
                    continue
                
                if dry_run:
                    self.stdout.write(
                        f"[DRY RUN] Would create: {emp_id} - {operation} at {punch_datetime}"
                    )
                    stats['punches_created'] += 1
                    continue
                
                # Create the punch record
                try:
                    with transaction.atomic():
                        AttendancePunch.objects.create(
                            employee=employee,
                            payroll_date=payroll_date,
                            punch_time=punch_datetime,
                            operation=operation,
                            raw_data={
                                'emp_id': emp_id,
                                'payroll_date': payroll_date_str,
                                'punch': punch,
                                'synced_at': timezone.now().isoformat()
                            }
                        )
                    stats['punches_created'] += 1
                    self.stdout.write(
                        f"Created: {emp_id} - {operation} at {punch_datetime}"
                    )
                except Exception as e:
                    logger.error(f"Failed to create punch record for {emp_id}: {e}")
                    stats['errors'] += 1
        
        return stats
    
    def _print_summary(self, stats: Dict[str, int], dry_run: bool):
        """Print a summary of the sync operation."""
        prefix = "[DRY RUN] " if dry_run else ""
        
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.NOTICE(f"{prefix}Sync Summary"))
        self.stdout.write("=" * 50)
        self.stdout.write(f"Employees found: {stats['employees_found']}")
        self.stdout.write(f"Employees not found: {stats['employees_not_found']}")
        self.stdout.write(f"Punches created: {stats['punches_created']}")
        self.stdout.write(f"Punches skipped (duplicates): {stats['punches_skipped']}")
        self.stdout.write(f"Errors: {stats['errors']}")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("\nThis was a dry run. No records were created.")
            )
        elif stats['errors'] > 0:
            self.stdout.write(
                self.style.ERROR(f"\nCompleted with {stats['errors']} errors.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("\nSync completed successfully!")
            )
