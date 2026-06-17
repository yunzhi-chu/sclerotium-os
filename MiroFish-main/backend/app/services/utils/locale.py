def t(key, **kw): return key
def get_language_instruction(lang): return f"Respond in {lang}"
def get_locale(lang="en"):
    class L: language="en"
    return L()
def set_locale(lang): pass
locale = "en"
