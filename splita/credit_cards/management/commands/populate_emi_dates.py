from django.core.management.base import BaseCommand
from credit_cards.models import CreditCardEMI
from loans.models import LoanEMI
from datetime import date
import calendar


class Command(BaseCommand):
    help = 'Populate start_date and end_date fields from existing due_date values'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate EMI dates...')
        
        # Update CreditCardEMI instances
        credit_card_count = 0
        for emi in CreditCardEMI.objects.filter(start_date__isnull=True):
            if emi.due_date and not emi.start_date:
                emi.start_date = emi.due_date
                
                # Calculate end_date
                if emi.total_duration:
                    end_month = emi.start_date.month + emi.total_duration - 1
                    end_year = emi.start_date.year + (end_month - 1) // 12
                    end_month = ((end_month - 1) % 12) + 1
                    try:
                        emi.end_date = date(end_year, end_month, emi.start_date.day)
                    except ValueError:
                        last_day = calendar.monthrange(end_year, end_month)[1]
                        emi.end_date = date(end_year, end_month, min(emi.start_date.day, last_day))
                
                emi.save()
                credit_card_count += 1
        
        # Update LoanEMI instances
        loan_count = 0
        for emi in LoanEMI.objects.filter(start_date__isnull=True):
            if emi.due_date and not emi.start_date:
                emi.start_date = emi.due_date
                
                # Calculate end_date
                if emi.total_duration:
                    end_month = emi.start_date.month + emi.total_duration - 1
                    end_year = emi.start_date.year + (end_month - 1) // 12
                    end_month = ((end_month - 1) % 12) + 1
                    try:
                        emi.end_date = date(end_year, end_month, emi.start_date.day)
                    except ValueError:
                        last_day = calendar.monthrange(end_year, end_month)[1]
                        emi.end_date = date(end_year, end_month, min(emi.start_date.day, last_day))
                
                emi.save()
                loan_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated dates for {credit_card_count} CreditCardEMI '
                f'and {loan_count} LoanEMI instances'
            )
        ) 