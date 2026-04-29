from .models import CustomUser, MedicalRecord, Appointment
from django.utils import timezone

def staff_status(request):
    context = {}
    if request.user.is_authenticated:
        if request.user.role == 'ADMIN':
            context.update({
                'global_staff_available': CustomUser.objects.filter(is_available=True).exclude(role='PATIENT').count(),
                'global_staff_offline': CustomUser.objects.filter(is_available=False).exclude(role='PATIENT').count(),
            })
        
        if request.user.role == 'DOCTOR':
            # Critical Inbox: Lab reports for patients in the queue today
            today = timezone.localdate()
            current_patient_ids = Appointment.objects.filter(
                doctor__user=request.user, 
                date=today, 
                status__in=['WAITING', 'IN_PROGRESS']
            ).values_list('patient_id', flat=True)
            
            critical_reports = MedicalRecord.objects.filter(
                patient_id__in=current_patient_ids,
                category='LAB_REPORT',
                uploaded_at__date=today
            ).count()
            
            context['critical_report_count'] = critical_reports
            
    return context
