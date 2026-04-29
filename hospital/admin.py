"""
admin.py — Government Hospital Kashipur
Full admin registration with custom actions, inlines, and EHR support.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    CustomUser, Dependent, DoctorProfile, Appointment,
    Medicine, Prescription, Feedback, StockAuditLog, MedicalRecord
)


# ─────────────────────────────────────────────
#  Custom User Admin
# ─────────────────────────────────────────────

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display  = ('username', 'get_full_name', 'role', 'mobile_no', 'is_approved', 'is_active', 'date_joined')
    list_filter   = ('role', 'is_approved', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'mobile_no', 'email')
    ordering      = ('-date_joined',)
    list_editable = ('is_approved', 'is_active')

    fieldsets = UserAdmin.fieldsets + (
        ('Hospital Info', {
            'fields': ('role', 'mobile_no', 'alt_mobile_no', 'address', 'is_approved')
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Hospital Info', {
            'fields': ('role', 'mobile_no', 'alt_mobile_no', 'address', 'first_name', 'last_name', 'email')
        }),
    )

    actions = ['approve_users', 'deactivate_users']

    def approve_users(self, request, queryset):
        updated = queryset.update(is_approved=True, is_active=True)
        self.message_user(request, f'{updated} user(s) approved successfully.')
    approve_users.short_description = '✅ Approve selected users'

    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} user(s) deactivated.')
    deactivate_users.short_description = '🚫 Deactivate selected users'


# ─────────────────────────────────────────────
#  Dependent Admin
# ─────────────────────────────────────────────

@admin.register(Dependent)
class DependentAdmin(admin.ModelAdmin):
    list_display  = ('name', 'patient', 'relation', 'gender', 'dob')
    list_filter   = ('relation', 'gender')
    search_fields = ('name', 'patient__username', 'patient__first_name')
    autocomplete_fields = ['patient']


# ─────────────────────────────────────────────
#  Doctor Profile Admin
# ─────────────────────────────────────────────

@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display    = ('user', 'specialization', 'department', 'available_days', 'max_patients_per_day')
    list_filter     = ('department',)
    search_fields   = ('user__first_name', 'user__last_name', 'specialization', 'department')
    autocomplete_fields = ['user']


# ─────────────────────────────────────────────
#  Appointment Admin
# ─────────────────────────────────────────────

class PrescriptionInline(admin.TabularInline):
    model          = Prescription
    extra          = 0
    readonly_fields = ('stock_status', 'prescribed_at')
    fields         = ('medicine', 'dosage', 'quantity_prescribed', 'duration_days', 'instructions', 'stock_status')

class MedicalRecordInline(admin.TabularInline):
    model   = MedicalRecord
    extra   = 0
    fields  = ('title', 'file', 'category', 'record_date', 'description')

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display    = ('token_number', 'patient_display', 'doctor', 'date', 'status', 'booking_time')
    list_filter     = ('status', 'date', 'doctor__department')
    search_fields   = ('patient__first_name', 'patient__last_name', 'doctor__user__first_name')
    date_hierarchy  = 'date'
    readonly_fields = ('token_number', 'booking_time')
    inlines         = [PrescriptionInline, MedicalRecordInline]

    def patient_display(self, obj):
        name = obj.patient_display_name
        if obj.dependent:
            return format_html('<span style="color:#e67e22">{} (Dep.)</span>', name)
        return name
    patient_display.short_description = 'Patient'

    actions = ['mark_completed', 'mark_cancelled']

    def mark_completed(self, request, queryset):
        queryset.update(status='COMPLETED')
    mark_completed.short_description = '✅ Mark as Completed'

    def mark_cancelled(self, request, queryset):
        queryset.update(status='CANCELLED')
    mark_cancelled.short_description = '❌ Mark as Cancelled'


# ─────────────────────────────────────────────
#  Medicine / Inventory Admin
# ─────────────────────────────────────────────

class StockAuditInline(admin.TabularInline):
    model          = StockAuditLog
    extra          = 0
    readonly_fields = ('pharmacist', 'action', 'quantity_changed', 'quantity_before', 'quantity_after', 'reason', 'timestamp')
    can_delete     = False
    max_num        = 0

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display    = ('medicine_name', 'batch_number', 'total_quantity', 'expiry_date', 'is_active', 'stock_badge', 'shelf_location')
    list_filter     = ('unit', 'expiry_date', 'is_active')
    search_fields   = ('medicine_name', 'generic_name', 'batch_number')
    readonly_fields = ('added_by', 'created_at')
    list_editable   = ('is_active',)
    inlines         = [StockAuditInline]

    def stock_badge(self, obj):
        if obj.is_expired:
            return format_html('<span style="background:#dc3545;color:white;padding:2px 8px;border-radius:4px">EXPIRED</span>')
        if obj.is_in_stock:
            return format_html('<span style="background:#198754;color:white;padding:2px 8px;border-radius:4px">✅ {}</span>', obj.total_quantity)
        return format_html('<span style="background:#dc3545;color:white;padding:2px 8px;border-radius:4px">OUT OF STOCK</span>')
    stock_badge.short_description = 'Stock Status'


# ─────────────────────────────────────────────
#  Prescription Admin
# ─────────────────────────────────────────────

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display    = ('medicine', 'appointment', 'dosage', 'quantity_prescribed', 'stock_status', 'prescribed_at')
    list_filter     = ('stock_status', 'prescribed_at')
    search_fields   = ('medicine__medicine_name', 'appointment__patient__first_name')
    readonly_fields = ('stock_status', 'prescribed_at', 'prescribed_by')


# ─────────────────────────────────────────────
#  Feedback Admin
# ─────────────────────────────────────────────

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display    = ('subject', 'sender', 'urgency_badge', 'is_resolved', 'created_at')
    list_filter     = ('urgency', 'is_resolved', 'created_at')
    search_fields   = ('subject', 'message', 'sender__username')
    readonly_fields = ('sender', 'created_at')
    fields          = ('sender', 'subject', 'message', 'urgency', 'file_attachment', 'is_resolved', 'admin_response', 'created_at')
    actions         = ['resolve_feedbacks']

    def urgency_badge(self, obj):
        colors = {'RED': '#dc3545', 'YELLOW': '#ffc107', 'GREEN': '#198754'}
        icons  = {'RED': '🔴', 'YELLOW': '🟡', 'GREEN': '🟢'}
        color  = colors.get(obj.urgency, '#6c757d')
        icon   = icons.get(obj.urgency, '')
        return format_html(
            '<span style="background:{};color:white;padding:2px 10px;border-radius:4px">{} {}</span>',
            color, icon, obj.get_urgency_display()
        )
    urgency_badge.short_description = 'Urgency'

    def resolve_feedbacks(self, request, queryset):
        queryset.update(is_resolved=True, resolved_by=request.user, resolved_at=timezone.now())
        self.message_user(request, f'{queryset.count()} feedback(s) marked as resolved.')
    resolve_feedbacks.short_description = '✅ Mark selected as Resolved'


# ─────────────────────────────────────────────
#  Stock Audit Log Admin
# ─────────────────────────────────────────────

@admin.register(StockAuditLog)
class StockAuditLogAdmin(admin.ModelAdmin):
    list_display    = ('timestamp', 'pharmacist', 'medicine', 'action', 'quantity_changed', 'quantity_before', 'quantity_after', 'reason')
    list_filter     = ('action', 'timestamp')
    search_fields   = ('pharmacist__username', 'medicine__medicine_name', 'reason')
    readonly_fields = ('pharmacist', 'medicine', 'action', 'quantity_changed', 'quantity_before', 'quantity_after', 'reason', 'timestamp', 'prescription')
    date_hierarchy  = 'timestamp'

    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False


# ─────────────────────────────────────────────
#  Medical Record Admin
# ─────────────────────────────────────────────

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display  = ('title', 'patient', 'category', 'record_date', 'uploaded_at')
    list_filter   = ('category', 'record_date', 'uploaded_at')
    search_fields = ('patient__username', 'patient__first_name', 'title')
    readonly_fields = ('uploaded_at',)
    autocomplete_fields = ('patient', 'appointment')


admin.site.site_header = "Government Hospital Kashipur — Administration"
admin.site.site_title  = "GHK Admin Portal"
admin.site.index_title = "Welcome to GHK Hospital Administration"
