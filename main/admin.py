import datetime

from django.contrib import admin

from .models import AdvUser, SuperRubric, SubRubric, Bb, AdditionalImage
from .utilities import send_activation_notification
from .forms import SubRubricForm


# ============================== For users ===================================
def send_activation_notifications(modeladmin, request, queryset):
    """
    Send letters for activation for not activated users.
    Function will be added to action list on admin page.
    """
    for rec in queryset:
        if not rec.is_activated:
            send_activation_notification(rec)
    modeladmin.message_user(request, 'Письма с оповещениями отправлены')


# add to actions list 'Отправка писем с оповещениями об активации'
send_activation_notifications.short_description =\
    'Отправка писем с оповещениями об активации'


class NonactivatedFilter(admin.SimpleListFilter):
    """
    Class for filter users by activation.
    To be announced in AdvUserAdmin model as filter.
    """
    title = 'Прошли активацию?'
    parameter_name = 'actstate'

    def lookups(self, request, model_admin):
        return (
            ('activated', 'Прошли'),
            ('threedays', 'Не прошли более 3-х дней'),
            ('week', 'Не прошли более недели')
        )

    def queryset(self, request, queryset):
        """
        Form list of users, who did not activate after sending letter
        for activation depending on time period
        """
        val = self.value()
        if val == 'activated':
            return queryset.filter(
                is_active=True,
                is_activated=True
            )
        elif val == 'threedays':
            d = datetime.date.today() - datetime.timedelta(days=3)
            return queryset.filter(
                is_active=False,
                is_activated=False,
                date_joined__date__lt=d
            )
        elif val == 'week':
            d = datetime.date.today() - datetime.timedelta(weeks=1)
            return queryset.filter(
                is_active=False,
                is_activated=False,
                date_joined__date__lt=d
            )


class AdvUserAdmin(admin.ModelAdmin):
    """For users in admin panel"""
    list_display = ('__str__', 'is_activated', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = (NonactivatedFilter,)
    fields = (('username', 'email'), ('first_name', 'last_name'),
              ('send_messages', 'is_active', 'is_activated'),
              ('is_staff', 'is_superuser'),
              'groups', 'user_permissions',
              ('last_login', 'date_joined'))
    readonly_fields = ('last_login', 'date_joined')
    actions = (send_activation_notifications,)


admin.site.register(AdvUser, AdvUserAdmin)


# ============================== Rubrics =====================================
class SubRubricInline(admin.TabularInline):
    """For formation under the selected heading of related subheadings"""
    model = SubRubric


class SuperRubricAdmin(admin.ModelAdmin):
    """Displaying data about SuperRubric in the admin panel."""
    exclude = ('super_rubric',)
    inlines = (SubRubricInline,)


admin.site.register(SuperRubric, SuperRubricAdmin)


class SubRubricAdmin(admin.ModelAdmin):
    """Displaying data about SubRubric in the admin panel."""
    form = SubRubricForm


admin.site.register(SubRubric, SubRubricAdmin)


# ================================= Ads ======================================
class AdditionalImageInline(admin.TabularInline):
    """Form info about additional images under ad on ad page"""
    model = AdditionalImage


class BbAdmin(admin.ModelAdmin):
    """Displaying data about ads in the admin panel."""
    list_display = ('rubric', 'title', 'content', 'author', 'created_at')
    fields = (
        ('rubric', 'author'),
        'title', 'content', 'price', 'contacts', 'image', 'is_active'
    )
    inlines = (AdditionalImageInline,)


admin.site.register(Bb, BbAdmin)
