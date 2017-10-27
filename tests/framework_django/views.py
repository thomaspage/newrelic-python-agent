from django.http import HttpResponse
from django.views.generic.base import View, TemplateView
from django.shortcuts import render
from django.core.exceptions import PermissionDenied

from newrelic.api.transaction import (get_browser_timing_header,
    get_browser_timing_footer)


def index(request):
    return HttpResponse('INDEX RESPONSE')


def exception(request):
    raise RuntimeError('exception')


def permission_denied(request):
    raise PermissionDenied()


class MyView(View):
    def get(self, request):
        return HttpResponse('CBV RESPONSE')


def deferred_cbv(request):
    return MyView.as_view()(request)


def html_insertion(request):
    return HttpResponse('<!DOCTYPE html><html><head>Some header</head>'
            '<body><h1>My First Heading</h1><p>My first paragraph.</p>'
            '</body></html>')


def html_insertion_content_length(request):
    content = ('<!DOCTYPE html><html><head>Some header</head>'
            '<body><h1>My First Heading</h1><p>My first paragraph.</p>'
            '</body></html>')
    response = HttpResponse(content)
    response['Content-Length'] = len(content)
    return response


def html_insertion_manual(request):
    header = get_browser_timing_header()
    footer = get_browser_timing_footer()

    header = get_browser_timing_header()
    footer = get_browser_timing_footer()

    assert header == ''
    assert footer == ''

    return HttpResponse('<!DOCTYPE html><html><head>Some header</head>'
            '<body><h1>My First Heading</h1><p>My first paragraph.</p>'
            '</body></html>')


def html_insertion_unnamed_attachment_header(request):
    response = HttpResponse('<!DOCTYPE html><html><head>Some header</head>'
            '<body><h1>My First Heading</h1><p>My first paragraph.</p>'
            '</body></html>')
    response['Content-Disposition'] = 'attachment'
    return response


def html_insertion_named_attachment_header(request):
    response = HttpResponse('<!DOCTYPE html><html><head>Some header</head>'
            '<body><h1>My First Heading</h1><p>My first paragraph.</p>'
            '</body></html>')
    response['Content-Disposition'] = 'Attachment; filename="X"'
    return response


def inclusion_tag(request):
    return render(request, 'main.html', {}, content_type="text/html")


def template_tags(request):
    return render(request, 'main.html', {}, content_type="text/html")


def render_exception_function(request):
    return render(request, 'render_exception.html')


class RenderExceptionClass(TemplateView):
    template_name = 'render_exception.html'


def gzip_html_insertion(request):
    # contents must be at least 200 bytes for gzip middleware to work
    contents = '*' * 200
    return HttpResponse('<!DOCTYPE html><html><head>Some header</head>'
        '<body><h1>My First Heading</h1><p>%s</p></body></html>' % contents)
