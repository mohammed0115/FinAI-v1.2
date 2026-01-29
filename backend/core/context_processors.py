"""
Template Context Processors
"""
from .translations import get_all_translations, get_translation


def language_context(request):
    """
    Add language and translations to template context.
    
    Language preference is stored in session.
    Arabic is the default and primary language.
    """
    # Get language from session, default to Arabic
    lang = request.session.get('language', 'ar')
    
    # Get direction based on language
    direction = 'rtl' if lang == 'ar' else 'ltr'
    html_lang = 'ar' if lang == 'ar' else 'en'
    
    return {
        'current_lang': lang,
        'direction': direction,
        'html_lang': html_lang,
        'is_arabic': lang == 'ar',
        'is_english': lang == 'en',
        't': get_all_translations(lang),  # All translations
    }
