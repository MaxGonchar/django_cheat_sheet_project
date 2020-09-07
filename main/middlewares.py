from .models import SubRubric


def bboard_context_processor(request):
    """
    Custom context_processor.
    Must be registered in settings.py, in constant 'TEMPLATES'
    add to context for templates additional information:
    "rubrics" - all rubrics
    "keyword" - word entered by user into the search-field
    "all" - summary list of parameters for URL for GET-request
    """
    context = {}
    context['rubrics'] = SubRubric.objects.all()
    context['keyword'] = ''
    context['all'] = ''
    # adding a keyword to the query parameter
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            context['keyword'] = '?keyword=' + keyword
            context['all'] = context['keyword']
    # summary list of parameters for URL for GET-request with "page" if exist
    # like ?keyword=keyword&page=page
    # "?" - start of parameters,
    # "&" - splitter
    if 'page' in request.GET:
        page = request.GET['page']
        if page != '1':
            if context['all']:
                context['all'] += '&page=' + page
            else:
                context['all'] = '?page=' + page

    return context
