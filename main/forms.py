from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from captcha.fields import CaptchaField

from .models import AdvUser, user_registrated, SuperRubric, SubRubric, Bb, \
    AdditionalImage, Comment


# ================== User's registration and changing data ===================
class ChangeUserInfoForm(forms.ModelForm):
    """
    Form for change user information.
    Field "email" described by fool announcement
    because we want to make it compulsory.
    Another fields described by fast announcement.
    """
    email = forms.EmailField(required=True, label='Адрес электронной почты')

    class Meta:
        model = AdvUser
        fields = (
            'username', 'email', 'first_name', 'last_name', 'send_messages'
        )


class RegisterUserForm(forms.ModelForm):
    """
    Form for user registration.
    Field "email", "password1" and "password2" described by fool announcement
    because we want to describe some params.
    "password_validation.password_validators_help_text_html()"
    describe demands for password from Django's validator.
    """
    email = forms.EmailField(required=True, label='Адрес электронной почты')
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput,
        help_text=password_validation.password_validators_help_text_html()
    )
    password2 = forms.CharField(
        label='Пароль (повторно)',
        widget=forms.PasswordInput,
        help_text='Введите пароль повторно для проверки'
    )

    # def clean_password1(self):
    #     """
    #     It was in book and it do not work
    #     :return:
    #     """
    #     password1 = self.cleaned_data['password1']
    #     if password1:
    #         password_validation.validate_password(password1)
    #     return password1

    def clean_password1(self):
        """
        Check password, using build-in "password_validation.validate_password"
        :return:
        """
        password1 = self.cleaned_data['password1']
        try:
            password_validation.validate_password(password1)
        except forms.ValidationError as error:
            # if password invalid - add error to errors list
            self.add_error('password1', error)
        return password1

    def clean(self):
        """
        Check is password1 equivalent to password2
        :return:
        """
        super().clean()
        password1 = self.cleaned_data['password1']
        password2 = self.cleaned_data['password2']
        if password1 and password2 and password1 != password2:
            errors = {
                'password2': ValidationError('веденные пароли не совпадают',
                                             code='password_mismatch')}
            raise ValidationError(errors)

    def save(self, commit=True):
        """
        Create user with "is_active" and "is_activated" are "False" by default
        and make signal to send the letter for confirm
        :param commit:
        :return:
        """
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        # "is_active" and "is_activated"
        # will change to "True" after registration user by letter
        user.is_active = False
        user.is_activated = False
        if commit:
            user.save()
        # signal to send letter
        user_registrated.send(RegisterUserForm, instance=user)
        return user

    class Meta:
        model = AdvUser
        fields = ('username', 'email', 'password1', 'password2', 'first_name',
                  'last_name', 'send_messages')


# ============================ Rubrics =======================================
class SubRubricForm(forms.ModelForm):
    """Form for work with sub_rubrics in admin page"""
    super_rubric = forms.ModelChoiceField(
        queryset=SuperRubric.objects.all(),
        empty_label=None,
        label='Надрубрика',
        required=True
    )

    class Meta:
        model = SubRubric
        fields = '__all__'


# ============================= Searching ====================================
class SearchForm(forms.Form):
    """Form for searching ads by word."""
    keyword = forms.CharField(required=False, max_length=20, label='')


# ================================ Ads =======================================
class BbForm(forms.ModelForm):
    """Form for adding ad by user on site"""

    class Meta:
        model = Bb
        fields = '__all__'
        widgets = {'author': forms.HiddenInput}


# additional fields for entering additional images
AIFormSet = inlineformset_factory(Bb, AdditionalImage, fields='__all__')


# ============================== Comments ====================================
class UserCommentForm(forms.ModelForm):
    """Adding comment under ad by registered user"""
    class Meta:
        model = Comment
        exclude = ('is_active',)
        widgets = {'bb': forms.HiddenInput}


class GuestCommentForm(forms.ModelForm):
    """Adding comment under ad by not registered user"""
    # for captcha field
    captcha = CaptchaField(label='Введите текст с картинки',
                           error_messages={'invalid': 'Неправильный текст'})

    class Meta:
        model = Comment
        exclude = ('is_active',)
        widgets = {'bb': forms.HiddenInput}
