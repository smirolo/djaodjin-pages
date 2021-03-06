# Copyright (c) 2015, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import os, zipfile

from django.conf import settings as django_settings
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.db.models import Q
from django.utils._os import safe_join
from rest_framework import status, generics
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response

from ..mixins import AccountMixin
from ..models import UploadedTemplate
from ..serializers import UploadedTemplateSerializer
from ..themes import install_theme


class UploadedTemplateMixin(AccountMixin):

    def get_queryset(self):
        queryset = UploadedTemplate.objects.filter(
            Q(account=self.account)|Q(account=None))
        return queryset


class UploadedTemplateListAPIView(UploadedTemplateMixin,
                                  generics.ListCreateAPIView):

    parser_classes = (FileUploadParser,)
    serializer_class = UploadedTemplateSerializer

    def post(self, request, *args, **kwargs):
        file_obj = request.data['file']
        theme_name = os.path.splitext(os.path.basename(file_obj.name))[0]
        templates_dir = safe_join(django_settings.TEMPLATE_DIRS[0], theme_name)
        if os.path.exists(templates_dir):
            # If we do not have an instance at this point, the directory
            # might still exist and belong to someone else when pages
            # tables are split amongst multiple databases.
            raise PermissionDenied("Theme %s already exists." % theme_name)
        if zipfile.is_zipfile(file_obj):
            with zipfile.ZipFile(file_obj) as zip_file:
                install_theme(theme_name, zip_file)
            UploadedTemplate.objects.create(
                name=theme_name, account=self.account)
            return Response({}, status=status.HTTP_204_NO_CONTENT)
        return Response({'info': "Invalid archive"},
            status=status.HTTP_400_BAD_REQUEST)


class UploadedTemplateAPIView(UploadedTemplateMixin,
                              generics.RetrieveUpdateAPIView):

    serializer_class = UploadedTemplateSerializer
    slug_url_kwarg = 'theme'

    def get_object(self):
        try:
            return self.get_queryset().get(
                name=self.kwargs.get(self.slug_url_kwarg))
        except UploadedTemplate.DoesNotExist:
            raise Http404("theme %s not found"
                % self.kwargs.get(self.slug_url_kwarg))
