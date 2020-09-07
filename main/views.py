from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import \
    LoginView, LogoutView, \
    PasswordChangeView, PasswordResetView, PasswordResetDoneView, \
    PasswordResetConfirmView, PasswordResetCompleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView
from django.views.generic.base import TemplateView
from django.views.generic.edit import UpdateView, DeleteView
from django.urls import reverse_lazy
from django.core.signing import BadSignature
from django.core.paginator import Paginator
from django.db.models import Q

from .models import AdvUser, SubRubric, Bb, Comment
from .forms import ChangeUserInfoForm, RegisterUserForm, SearchForm, BbForm, \
    AIFormSet, UserCommentForm, GuestCommentForm
from .utilities import signer


def index(request):
    """
    The page that opens, when entering the site.
    Page contains 10 last ads.
    """
    bbs = Bb.objects.filter(is_active=True)[:10]
    context = {'bbs': bbs}
    return render(request, 'main/index.html', context)


def other_page(request, page):
    """
    To display sub pages.
    'page' is template name
     (for example {% url 'main:other' page='about' %} )
     """
    try:
        template = get_template('main/' + page + '.html')
    except TemplateDoesNotExist:
        raise Http404
    return HttpResponse(template.render(request=request))


# ====================== User's registration / deleting ======================
class RegisterUserView(CreateView):
    """
    User register handler.
    """
    model = AdvUser
    template_name = 'main/register_user.html'
    form_class = RegisterUserForm
    success_url = reverse_lazy('main:register_done')


def user_activate(request, sign):
    """User's activation handler"""
    try:
        username = signer.unsign(sign)
    except BadSignature:  # if user's sign is bad
        return render(request, 'main/bad_signature.html')

    user = get_object_or_404(AdvUser, username=username)

    if user.is_activated:  # if user is already activated
        template = 'main/user_is_activated.html'
    else:  # user's activation
        template = 'main/activation_done.html'
        user.is_active = True
        user.is_activated = True
        user.save()

    return render(request, template)


class RegisterDoneView(TemplateView):
    """Template output with a message about successful registration"""
    template_name = 'main/register_done.html'


class DeleteUserView(LoginRequiredMixin, DeleteView):
    """
    User's deleting handler.
    "dispatch" - for extraction user_id from request. (inherited from "View")
    "get_object" - get user by "user_id"
    "post" - logout before deleting + create success message
    """
    model = AdvUser
    template_name = 'main/delete_user.html'
    success_url = reverse_lazy('main:index')

    def dispatch(self, request, *args, **kwargs):
        self.user_id = request.user.pk
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.add_message(request, messages.SUCCESS, 'Пользователь удален')
        return super().post(request, *args, **kwargs)

    def get_object(self, queryset=None):
        if not queryset:
            queryset = self.get_queryset()
        return get_object_or_404(queryset, pk=self.user_id)


# ========================== Log in / log out ================================
class BBLoginView(LoginView):
    """Handler login procedure"""
    template_name = 'main/login.html'  # Indicate our custom template name


class BBLogoutView(LoginRequiredMixin, LogoutView):
    """
    Handler logout procedure
    LoginRequiredMixin - only authenticated users need to logout
    """
    template_name = 'main/logout.html'


# ===================== Password and user's info changing ====================
class ChangeUserInfoView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    """
    User Data Change handler.
    "dispatch" - for extraction user_id from request.
    (inherited from "View")
    "get_object" - extract user instance for handler.
    (inherited from "SingleObjectMixin")
    "SuccessMessageMixin" - for pop-up success messages.
    """
    model = AdvUser
    template_name = 'main/change_user_info.html'
    form_class = ChangeUserInfoForm
    success_url = reverse_lazy('main:profile')
    success_message = 'Личные данные пользователя изменены.'

    def dispatch(self, request, *args, **kwargs):
        self.user_id = request.user.pk
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        if not queryset:
            queryset = self.get_queryset()
        return get_object_or_404(queryset, pk=self.user_id)


class BBPasswordChangeView(
    SuccessMessageMixin,
    LoginRequiredMixin,
    PasswordChangeView
):
    """
    User password change handler.
    """
    template_name = 'main/password_change.html'
    success_url = reverse_lazy('main:profile')
    success_message = 'Пароль пользователя изменен.'


class BBPasswordResetView(SuccessMessageMixin, PasswordResetView):
    """
    Handler takes user's email, compares with DB, if success -
    send message with linc to reset psw.
    "template_name" - template with form for email.
    "subject_template_name" - subject of letter.
    "email_template_name" - body of letter
    """
    template_name = 'main/password_reset.html'
    subject_template_name = 'email/reset_password_subject.txt'
    email_template_name = 'email/reset_password_body.html'
    success_url = reverse_lazy('main:password_reset_done')


class BBPasswordResetDoneView(PasswordResetDoneView):
    """
    display page with message, that letter was sending.
    """
    template_name = 'main/password_reset_done.html'


class BBPasswordResetConfirmView(PasswordResetConfirmView):
    """
    Handler takes and validates new password.
    "template_name" - page with form for entering new password.
    User go here from link in letter.
    """
    template_name = 'main/password_reset_confirm.html'
    success_url = reverse_lazy('main:password_reset_complete')


class BBPasswordResetCompleteView(PasswordResetCompleteView):
    """
    display page with message, that password was changed.
    """
    template_name = 'main/password_reset_complete.html'


# ============================ Data for guests ===============================
def by_rubric(request, pk):
    """
    Displays all ads belonging to a user-selected category.
    The controller implements a keyword search in the title and body of the ad.
    There is also a paginator.
    :param request:
    :param pk: SubRubric pk
    :return:
    """

    rubric = get_object_or_404(SubRubric, pk=pk)
    bbs = Bb.objects.filter(is_active=True, rubric=pk)

    # filtering ads by word entered by the visitor
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        # The Q object (django.db.models.Q) is an object used to encapsulate
        # multiple named arguments for filtering.
        # The next line creates a new set of filter arguments ("q")
        # that will allow you to select announcements
        # that contain the search word
        # in the "title" or ("|") "content".
        q = Q(title__icontains=keyword) | Q(content__icontains=keyword)
        bbs = bbs.filter(q)
    else:
        keyword = ''
    form = SearchForm(initial={'keyword': keyword})

    paginator = Paginator(bbs, 2)  # create Paginator object for 2 ads in page
    if 'page' in request.GET:
        page_num = request.GET['page']
    else:
        page_num = 1

    page = paginator.get_page(page_num)
    context = {
        'rubric': rubric,
        'page': page,
        'bbs': page.object_list,
        'form': form
    }

    return render(request, 'main/by_rubric.html', context)


def detail(request, rubric_pk, pk):
    """
    Contain ad's info, additional images.
    Also contain comments and field for adding new comments.
    :param request:
    :param rubric_pk:
    :param pk:
    :return:
    """
    bb = get_object_or_404(Bb, pk=pk)  # ad
    ais = bb.additionalimage_set.all()  # ad's images
    comments = Comment.objects.filter(bb=pk, is_active=True)
    initial = {'bb': bb.pk}
    # choice of form depending on whether the user is registered
    # or not creates a comment
    if request.user.is_authenticated:
        initial['author'] = request.user.username
        form_class = UserCommentForm
    else:
        form_class = GuestCommentForm
    form = form_class(initial=initial)

    if request.method == 'POST':
        c_form = form_class(request.POST)
        if c_form.is_valid():
            c_form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                'Комментарий добавлен'
            )
        else:
            form = c_form
            messages.add_message(
                request,
                messages.WARNING,
                'Комментарий не добавлен'
            )

    context = {'bb': bb, 'ais': ais, 'comments': comments, 'form': form}
    return render(request, 'main/detail.html', context)


# =================== Data and functional for ad's owners ====================
@login_required
def profile(request):
    """
    Profile of registered user, shows user's ads.
    :param request:
    :return:
    """
    bbs = Bb.objects.filter(author=request.user.pk)
    context = {'bbs': bbs}
    return render(request, 'main/profile.html', context)


@login_required
def profile_bb_detail(request, pk):
    """
    Ad's detail for owner
    :param request:
    :param pk: ad's pk
    :return:
    """
    bb = get_object_or_404(Bb, pk=pk)  # ad
    ais = bb.additionalimage_set.all()  # ad's images
    context = {'bb': bb, 'ais': ais}
    return render(request, 'main/profile_bb_detail.html', context)


@login_required
def profile_bb_add(request):
    """Page for adding ad by registered user. Allow from profile-page"""
    if request.method == 'POST':
        # "request.FILES" transmit images
        form = BbForm(request.POST, request.FILES)
        if form.is_valid():
            bb = form.save()
            # at first we create an save bb-instance
            # at second we transmit bb to "formset"
            # it need to chain images from "formset" with bb-instance
            formset = AIFormSet(request.POST, request.FILES, instance=bb)
            if formset.is_valid():
                formset.save()
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    'Объявление добавлено'
                )
                return redirect('main:profile')
    else:
        # author determines automatically,
        # user can non create ad for another user
        form = BbForm(initial={'author': request.user.pk})
        formset = AIFormSet()
    context = {'form': form, 'formset': formset}
    return render(request, 'main/profile_bb_add.html', context)


@login_required
def profile_bb_change(request, pk):
    """Page for changing ad by registered user. Allow from user's ad-page"""
    bb = get_object_or_404(Bb, pk=pk)
    if request.method == 'POST':
        form = BbForm(request.POST, request.FILES, instance=bb)
        if form.is_valid():
            bb = form.save()
            formset = AIFormSet(request.POST, request.FILES, instance=bb)
            if formset.is_valid():
                formset.save()
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    'Объявление изменено'
                )
                return redirect('main:profile')
    else:
        form = BbForm(instance=bb)
        formset = AIFormSet(instance=bb)
    context = {'form': form, 'formset': formset}
    return render(request, 'main/profile_bb_change.html', context)


@login_required
def profile_bb_delete(request, pk):
    """Page for deleting ad by registered user. Allow from user's ad-page"""
    bb = get_object_or_404(Bb, pk=pk)
    if request.method == 'POST':
        bb.delete()
        messages.add_message(request, messages.SUCCESS, 'Объявление удалено')
        return redirect('main:profile')
    else:
        context = {'bb': bb}
        return render(request, 'main/profile_bb_delete.html', context)
