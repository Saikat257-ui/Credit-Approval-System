from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Customer, Loan
from .serializers import CustomerSerializer, LoanSerializer
from django.db.models import Sum
from datetime import date
import math

# Helper: Compound interest EMI calculation
def calculate_emi(principal, rate, tenure):
    monthly_rate = rate / (12 * 100)
    emi = principal * monthly_rate * pow(1 + monthly_rate, tenure) / (pow(1 + monthly_rate, tenure) - 1)
    return round(emi, 2)

# Helper: Credit score calculation
def calculate_credit_score(customer, loans):
    if not loans.exists():
        return 100  # No loans, perfect score
    score = 100
    # i. Past Loans paid on time
    total_loans = loans.count()
    on_time_ratio = sum([min(loan.emis_paid_on_time / loan.tenure, 1) for loan in loans]) / total_loans
    score *= on_time_ratio
    # ii. No of loans taken in past
    if total_loans > 5:
        score -= (total_loans - 5) * 2
    # iii. Loan activity in current year
    current_year = date.today().year
    current_year_loans = loans.filter(start_date__year=current_year).count()
    if current_year_loans > 2:
        score -= (current_year_loans - 2) * 5
    # iv. Loan approved volume
    total_loan_amount = loans.aggregate(Sum('loan_amount'))['loan_amount__sum'] or 0
    if total_loan_amount > customer.approved_limit:
        score -= 20
    # v. If sum of current loans > approved limit, credit score = 0
    active_loans = loans.filter(end_date__gte=date.today())
    active_loan_sum = active_loans.aggregate(Sum('loan_amount'))['loan_amount__sum'] or 0
    if active_loan_sum > customer.approved_limit:
        return 0
    return max(0, int(score))

class RegisterView(APIView):
    def post(self, request):
        data = request.data
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        age = data.get('age')
        monthly_income = data.get('monthly_income')
        phone_number = data.get('phone_number')
        if not all([first_name, last_name, age, monthly_income, phone_number]):
            return Response({'error': 'All fields are required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if phone number already exists
        if Customer.objects.filter(phone_number=phone_number).exists():
            return Response({'error': 'Phone number already registered.'}, status=status.HTTP_400_BAD_REQUEST)

        rate_limit = 36 * int(monthly_income)
        approved_limit = round(rate_limit / 100000.0) * 100000
        try:
            customer = Customer.objects.create(
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                age=age,
                monthly_salary=monthly_income,
                approved_limit=approved_limit
            )
        except Exception as e:
            return Response({'error': f'Failed to create customer: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        resp = {
            'customer_id': customer.customer_id,
            'name': f"{customer.first_name} {customer.last_name}",
            'age': customer.age,
            'monthly_income': monthly_income,
            'approved_limit': approved_limit,
            'phone_number': phone_number
        }
        return Response(resp, status=status.HTTP_201_CREATED)

class CheckEligibilityView(APIView):
    def post(self, request):
        data = request.data
        customer_id = data.get('customer_id')
        loan_amount = float(data.get('loan_amount'))
        interest_rate = float(data.get('interest_rate'))
        tenure = int(data.get('tenure'))
        try:
            customer = Customer.objects.get(customer_id=customer_id)  # type: ignore
        except Customer.DoesNotExist:  # type: ignore
            return Response({'error': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)
        loans = Loan.objects.filter(customer=customer)  # type: ignore
        credit_score = calculate_credit_score(customer, loans)
        # If sum of all current EMIs > 50% of monthly salary, don’t approve any loans
        active_loans = loans.filter(end_date__gte=date.today())
        total_emi = sum([loan.monthly_repayment for loan in active_loans])
        if total_emi > 0.5 * customer.monthly_salary:
            return Response({
                'customer_id': customer_id,
                'approval': False,
                'interest_rate': interest_rate,
                'corrected_interest_rate': None,
                'tenure': tenure,
                'monthly_installment': None,
                'message': 'EMI exceeds 50% of monthly salary.'
            }, status=status.HTTP_200_OK)
        approval = False
        corrected_interest_rate = interest_rate
        message = ''
        if credit_score > 50:
            approval = True
        elif 50 >= credit_score > 30:
            if interest_rate > 12:
                approval = True
            else:
                corrected_interest_rate = 12.1
                message = 'Interest rate too low for this credit score.'
        elif 30 >= credit_score > 10:
            if interest_rate > 16:
                approval = True
            else:
                corrected_interest_rate = 16.1
                message = 'Interest rate too low for this credit score.'
        elif credit_score <= 10:
            approval = False
            message = 'Credit score too low.'
        emi = calculate_emi(loan_amount, corrected_interest_rate, tenure) if approval else None
        return Response({
            'customer_id': customer_id,
            'approval': approval,
            'interest_rate': interest_rate,
            'corrected_interest_rate': corrected_interest_rate if corrected_interest_rate != interest_rate else None,
            'tenure': tenure,
            'monthly_installment': emi,
            'message': message
        }, status=status.HTTP_200_OK)

class CreateLoanView(APIView):
    def post(self, request):
        data = request.data
        customer_id = data.get('customer_id')
        loan_amount = float(data.get('loan_amount'))
        interest_rate = float(data.get('interest_rate'))
        tenure = int(data.get('tenure'))
        try:
            customer = Customer.objects.get(customer_id=customer_id)  # type: ignore
        except Customer.DoesNotExist:  # type: ignore
            return Response({'error': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)
        loans = Loan.objects.filter(customer=customer)  # type: ignore
        credit_score = calculate_credit_score(customer, loans)
        active_loans = loans.filter(end_date__gte=date.today())
        total_emi = sum([loan.monthly_repayment for loan in active_loans])
        if total_emi > 0.5 * customer.monthly_salary:
            return Response({
                'loan_id': None,
                'customer_id': customer_id,
                'loan_approved': False,
                'message': 'EMI exceeds 50% of monthly salary.',
                'monthly_installment': None
            }, status=status.HTTP_200_OK)
        approval = False
        corrected_interest_rate = interest_rate
        message = ''
        if credit_score > 50:
            approval = True
        elif 50 >= credit_score > 30:
            if interest_rate > 12:
                approval = True
            else:
                corrected_interest_rate = 12.1
                message = 'Interest rate too low for this credit score.'
        elif 30 >= credit_score > 10:
            if interest_rate > 16:
                approval = True
            else:
                corrected_interest_rate = 16.1
                message = 'Interest rate too low for this credit score.'
        elif credit_score <= 10:
            approval = False
            message = 'Credit score too low.'
        emi = calculate_emi(loan_amount, corrected_interest_rate, tenure) if approval else None
        if approval:
            loan = Loan.objects.create(  # type: ignore
                customer=customer,
                loan_amount=loan_amount,
                tenure=tenure,
                interest_rate=corrected_interest_rate,
                monthly_repayment=emi,
                emis_paid_on_time=0,
                start_date=date.today(),
                end_date=date(date.today().year + tenure // 12, (date.today().month + tenure % 12 - 1) % 12 + 1, date.today().day)
            )
            customer.current_debt += loan_amount
            customer.save()
            return Response({
                'loan_id': loan.loan_id,
                'customer_id': customer_id,
                'loan_approved': True,
                'message': 'Loan approved.',
                'monthly_installment': emi
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'loan_id': None,
                'customer_id': customer_id,
                'loan_approved': False,
                'message': message,
                'monthly_installment': None
            }, status=status.HTTP_200_OK)

class ViewLoansView(APIView):
    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(customer_id=customer_id)  # type: ignore
        except Customer.DoesNotExist:  # type: ignore
            return Response({'error': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)
        loans = Loan.objects.filter(customer=customer)  # type: ignore
        result = []
        for loan in loans:
            repayments_left = loan.tenure - loan.emis_paid_on_time
            result.append({
                'loan_id': loan.loan_id,
                'loan_amount': loan.loan_amount,
                'interest_rate': loan.interest_rate,
                'monthly_installment': loan.monthly_repayment,
                'repayments_left': repayments_left
            })
        return Response(result, status=status.HTTP_200_OK) 