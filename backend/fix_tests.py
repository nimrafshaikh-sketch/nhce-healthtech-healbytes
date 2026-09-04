import glob

for f in glob.glob('apps/*/tests/*.py'):
    with open(f, 'r') as fp:
        c = fp.read()
    
    # Fix dates of birth
    names_to_fix = ["Hank", "Patient 1", "John Doe", "Jane Doe", "Alice", "Bob"]
    for name in names_to_fix:
        c = c.replace(f'name="{name}"', f'name="{name}", date_of_birth="1990-01-01"')
    
    # Fix auth payloads
    if 'test_auth.py' in f:
        c = c.replace('"email": "doc@example.com",', '"email": "doc@example.com", "name": "Dr. Doc",')
        c = c.replace('"email": "test_user@example.com",', '"email": "test_user@example.com", "name": "Test User",')

    with open(f, 'w') as fp:
        fp.write(c)
