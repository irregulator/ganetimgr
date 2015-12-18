# -*- coding: utf-8 -*- vim:fileencoding=utf-8:
# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from django.conf import settings
from django.contrib.sites.models import RequestSite
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.core.mail import mail_managers
from registration import signals
from registration.models import RegistrationProfile
from registration.views import RegistrationView
from apply.models import Organization
from accounts.forms import RegistrationForm
from django.core.urlresolvers import reverse_lazy
from django.contrib import messages
from django.utils.translation import ugettext as _


class GanetimgrRegistrationView(RegistrationView):
    form_class = RegistrationForm
    success_url = reverse_lazy('user-instances')

    def register(self, request, form, **kwargs):
        if form.is_valid():
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password1')
            firstname = form.cleaned_data.get('name')
            lastname = form.cleaned_data.get('surname')
            organization = form.cleaned_data.get('organization')
            telephone = form.cleaned_data.get('phone')
        if Site._meta.installed:
            site = Site.objects.get_current()
        else:
            site = RequestSite(request)
        new_user = RegistrationProfile.objects.create_inactive_user(
            site,
            send_email=False,
            **{
                'username': username,
                'password': password,
                'email': email,
                'first_name': firstname,
                'last_name': lastname,
            }
        )
        new_user.first_name = firstname
        new_user.last_name = lastname
        new_user.save()
        profile = new_user.userprofile
        try:
            organization = Organization.objects.get(title=organization)
        except Organization.DoesNotExist:
            pass
        else:
            profile.organization = organization
        profile.telephone = telephone
        profile.save()
        subject = render_to_string(
            'registration/activation_email_subject.txt',
            {'site': site}
        )
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        registration_profile = RegistrationProfile.objects.get(user=new_user)
        message = render_to_string(
            'registration/activation_email.txt',
            {
                'activation_key': registration_profile.activation_key,
                'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
                'site': site,
                'user': new_user
            }
        )
        mail_managers(subject, message)
        signals.user_registered.send(
            sender=self.__class__,
            user=new_user,
            request=request
        )
        messages.add_message(
            request,
            messages.INFO,
            _(
                'An email has been sent to the system administrator.'
                ' You will be soon notified about the activation of'
                ' your account.'
            )
        )
        return new_user