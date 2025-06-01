from django.core.management.base import BaseCommand
from notifications.models import NotificationTemplate


class Command(BaseCommand):
    help = 'Create initial notification templates'

    def handle(self, *args, **options):
        templates = [
            {
                'template_type': 'EMI_REMINDER',
                'email_subject': 'EMI Payment Reminder - Due {due_date}',
                'email_body': '''Dear {user_name},

This is a friendly reminder that your EMI payment is due on {due_date}.

Payment Details:
- Amount: ₹{emi_amount}
- Due Date: {due_date}
- Source: {card_name}{loan_name}

Please ensure timely payment to avoid late fees.

Best regards,
Splita Team''',
                'push_title': 'EMI Payment Due',
                'push_body': 'Your EMI of ₹{emi_amount} is due on {due_date}',
                'sms_body': 'EMI Alert: ₹{emi_amount} due on {due_date} for {card_name}{loan_name}. Pay now to avoid late fees.',
                'variables_help': 'Available variables: {user_name}, {emi_amount}, {due_date}, {card_name}, {loan_name}'
            },
            {
                'template_type': 'PAYMENT_CONFIRMATION',
                'email_subject': 'Payment Confirmation - ₹{payment_amount}',
                'email_body': '''Dear {user_name},

Your payment has been successfully processed.

Payment Details:
- Amount Paid: ₹{payment_amount}
- Payment Date: {payment_date}
- EMI Amount: ₹{emi_amount}
- Due Date: {due_date}

Thank you for your timely payment.

Best regards,
Splita Team''',
                'push_title': 'Payment Successful',
                'push_body': 'Payment of ₹{payment_amount} processed successfully',
                'sms_body': 'Payment Confirmed: ₹{payment_amount} paid on {payment_date}. Thank you!',
                'variables_help': 'Available variables: {user_name}, {payment_amount}, {payment_date}, {emi_amount}, {due_date}'
            },
            {
                'template_type': 'OVERDUE_ALERT',
                'email_subject': 'URGENT: Overdue EMI Payment - {days_overdue} days',
                'email_body': '''Dear {user_name},

Your EMI payment is now {days_overdue} days overdue.

Payment Details:
- Amount: ₹{emi_amount}
- Original Due Date: {due_date}
- Source: {card_name}{loan_name}

Please make the payment immediately to avoid additional charges and impact on your credit score.

Best regards,
Splita Team''',
                'push_title': 'Overdue Payment Alert',
                'push_body': 'Your EMI of ₹{emi_amount} is {days_overdue} days overdue',
                'sms_body': 'URGENT: EMI ₹{emi_amount} overdue by {days_overdue} days. Pay now to avoid penalties.',
                'variables_help': 'Available variables: {user_name}, {emi_amount}, {due_date}, {days_overdue}, {card_name}, {loan_name}'
            },
            {
                'template_type': 'CREDIT_UTILIZATION',
                'email_subject': 'High Credit Utilization Alert - {utilization_percentage}%',
                'email_body': '''Dear {user_name},

Your credit card utilization is currently high.

Card Details:
- Card: {card_name}
- Current Balance: ₹{current_balance}
- Credit Limit: ₹{credit_limit}
- Utilization: {utilization_percentage}%

Consider paying down your balance to maintain a healthy credit score.

Best regards,
Splita Team''',
                'push_title': 'High Credit Utilization',
                'push_body': '{card_name} utilization is {utilization_percentage}%',
                'sms_body': 'Credit Alert: {card_name} utilization at {utilization_percentage}%. Consider paying down balance.',
                'variables_help': 'Available variables: {user_name}, {card_name}, {current_balance}, {credit_limit}, {utilization_percentage}'
            },
            {
                'template_type': 'LOAN_COMPLETION',
                'email_subject': 'Congratulations! Loan Completed',
                'email_body': '''Dear {user_name},

Congratulations! You have successfully completed your loan.

Loan Details:
- Loan: {loan_name}
- Principal Amount: ₹{principal_amount}
- Total Paid: ₹{total_paid}

Thank you for your commitment to timely payments.

Best regards,
Splita Team''',
                'push_title': 'Loan Completed!',
                'push_body': 'Congratulations! Your {loan_name} is now fully paid',
                'sms_body': 'Congratulations! {loan_name} completed. Total paid: ₹{total_paid}',
                'variables_help': 'Available variables: {user_name}, {loan_name}, {principal_amount}, {total_paid}'
            },
            {
                'template_type': 'WELCOME',
                'email_subject': 'Welcome to Splita - Your Personal Finance Manager',
                'email_body': '''Dear {user_name},

Welcome to Splita! We're excited to help you manage your personal finances.

With Splita, you can:
- Track credit cards and loans
- Manage EMI schedules
- Receive payment reminders
- Monitor credit utilization

Get started by adding your first credit card or loan.

Best regards,
Splita Team''',
                'push_title': 'Welcome to Splita!',
                'push_body': 'Start managing your finances with Splita',
                'sms_body': 'Welcome to Splita! Start managing your credit cards and loans today.',
                'variables_help': 'Available variables: {user_name}'
            }
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates:
            template, created = NotificationTemplate.objects.get_or_create(
                template_type=template_data['template_type'],
                defaults=template_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created template: {template.template_type}')
                )
            else:
                # Update existing template
                for key, value in template_data.items():
                    setattr(template, key, value)
                template.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated template: {template.template_type}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {created_count + updated_count} templates '
                f'({created_count} created, {updated_count} updated)'
            )
        ) 