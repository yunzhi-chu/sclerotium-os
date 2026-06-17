"""Import every .py file in src/ to verify no import errors."""
import sys, os, importlib
sys.path.insert(0, '.')
errors = []
success = 0
for root, dirs, files in os.walk('src'):
    for f in sorted(files):
        if f.endswith('.py') and f != '__init__.py':
            mod = os.path.join(root, f).replace(os.sep, '.').replace('.py', '')
            try:
                importlib.import_module(mod)
                success += 1
            except Exception as e:
                errors.append(f'{mod}: {type(e).__name__}: {str(e)[:120]}')
print(f'Imported: {success} modules OK')
if errors:
    print(f'\nErrors: {len(errors)}')
    for e in errors:
        print(f'  {e}')
else:
    print('All modules import successfully!')
