from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import AbstractUser
from django.dispatch import Signal

from .utilities import send_activation_notification, get_timestamp_path,\
    send_new_comment_notification


# ============================== Users =======================================
class AdvUser(AbstractUser):
    """
    inheriting from the build-in abstract user model
    """
    is_activated = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name='Прошел активацию?'
    )
    send_messages = models.BooleanField(
        default=True,
        verbose_name='Слать оповещения о новых комментариях?'
    )

    def delete(self, *args, **kwargs):
        """Explicitly deleting user ads when deleting that user"""
        for bb in self.bb_set.all():
            bb.delete()
        super().delete(*args, **kwargs)

    class Meta(AbstractUser.Meta):
        ...


# create signal for user's registration
# the signal will be triggered in the registration form
# when saving a new user
user_registrated = Signal(providing_args=['instance'])


def user_registrated_dispatcher(sender, **kwargs):
    """Sending letter for user's activation"""
    send_activation_notification(kwargs['instance'])


# attach signal to function
user_registrated.connect(user_registrated_dispatcher)


# ============================= Rubrics ======================================
class Rubric(models.Model):
    """Base model for all rubrics"""
    name = models.CharField(
        max_length=20,
        db_index=True,
        unique=True,
        verbose_name='Название'
    )
    # "order" - number witch mean order of following
    order = models.SmallIntegerField(
        default=0,
        db_index=True,
        verbose_name='Порядок'
    )
    # "super_rubric" - filled in in case recording hase sub-rubric
    super_rubric = models.ForeignKey(
        'SuperRubric',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Надрубрика'
    )


class SuperRubricManager(models.Manager):
    """
    Record manager, which specifies filtering conditions for records
    processed by the model SuperRubric
    """

    def get_queryset(self):
        return super().get_queryset().filter(super_rubric__isnull=True)


class SuperRubric(Rubric):
    """General rubrics"""
    objects = SuperRubricManager()

    def __str__(self):
        return self.name

    class Meta:
        proxy = True
        ordering = ('order', 'name')
        verbose_name = 'Надрубрика'
        verbose_name_plural = 'Надрубрики'


class SubRubricManager(models.Manager):
    """
    Record manager, which specifies filtering conditions for records
    processed by the model SubRubric
    """

    def get_queryset(self):
        return super().get_queryset().filter(super_rubric__isnull=False)


class SubRubric(Rubric):
    """Sub rubrics of general rubrics"""
    objects = SubRubricManager()

    def __str__(self):
        return f'{self.super_rubric.name} - {self.name}'

    class Meta:
        proxy = True
        ordering = (
            'super_rubric__order',
            'super_rubric__name',
            'order',
            'name'
        )
        verbose_name = 'Подрубрика'
        verbose_name_plural = 'Подрубрики'


# ================================= Ads ======================================
class Bb(models.Model):
    """Model for advertisements"""
    rubric = models.ForeignKey(
        SubRubric,
        on_delete=models.PROTECT,
        verbose_name='Рубрика'
    )
    title = models.CharField(max_length=40, verbose_name='Товар')
    content = models.TextField(verbose_name='Описание')
    price = models.FloatField(default=0, verbose_name='Цена')
    contacts = models.TextField(verbose_name='Контакты')
    image = models.ImageField(
        blank=True,
        upload_to=get_timestamp_path,
        verbose_name='Изображения'
    )
    author = models.ForeignKey(
        AdvUser,
        on_delete=models.CASCADE,
        verbose_name='Автор объявления'
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name='Выводить в списке?'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Опубликовано'
    )

    def delete(self, *args, **kwargs):
        """
        Before deleting of advertisement we need delete all images
        of this advertisement When the 'delete ()' method is called,
        a 'post_delete' signal is raised,
        handled by the 'django-cleanup' application, which,
        in response, will delete all the files that were just deleted.
        """
        for ai in self.additionalimage_set.all():
            ai.delete()
        super().delete(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Объявления'
        verbose_name = 'Объявление'
        ordering = ['-created_at']


class AdditionalImage(models.Model):
    """Model for additional images"""
    bb = models.ForeignKey(
        Bb,
        on_delete=models.CASCADE,
        verbose_name='Объявление'
    )
    images = models.ImageField(
        upload_to=get_timestamp_path,
        verbose_name='Изображение'
    )

    class Meta:
        verbose_name_plural = 'Дополнительные иллюстрации'
        verbose_name = 'Дополнительная иллюстрация'


# =============================== Comments ===================================
class Comment(models.Model):
    """Model for comments"""
    bb = models.ForeignKey(
        Bb,
        on_delete=models.CASCADE,
        verbose_name='Объявление'
    )
    author = models.CharField(max_length=30, verbose_name='Автор')
    content = models.TextField(verbose_name='Содержание')
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name='Выводить на экран'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Опубликован'
    )

    class Meta:
        verbose_name_plural = 'Комментарии'
        verbose_name = 'Комментарий'
        ordering = ['-created_at']


def post_save_dispatcher(sender, **kwargs):
    """Sending letter about new comment to ad's owner."""
    author = kwargs['instance'].bb.author
    if kwargs['created'] and author.send_messages:
        send_new_comment_notification(kwargs['instance'])


# to send a letter about a new comment, we use the built-in signal "post_save"
# that will be triggered when the comment is saved
post_save.connect(post_save_dispatcher, sender=Comment)
