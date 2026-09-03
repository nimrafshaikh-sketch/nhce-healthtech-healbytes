import glob
import re

for f in glob.glob('apps/*/tests/*.py'):
    with open(f, 'r') as fp:
        c = fp.read()
    
    # regex to find Patient.objects.create(...) that don't have date_of_birth
    def repl_patient_create(m):
        inner = m.group(1)
        if 'date_of_birth' not in inner:
            return f'Patient.objects.create({inner}, date_of_birth="1990-01-01")'
        return m.group(0)
    
    c = re.sub(r'Patient\.objects\.create\((.*?)\)', repl_patient_create, c, flags=re.DOTALL)
    
    # Fix self.client.post payloads for patient creation
    if 'test_patients.py' in f:
        # We need to make sure the POST payload has date_of_birth
        c = c.replace('"name": "New Patient"', '"name": "New Patient", "date_of_birth": "1990-01-01"')
        c = c.replace('"name": "Jane Doe"', '"name": "Jane Doe", "date_of_birth": "1990-01-01"')

    with open(f, 'w') as fp:
        fp.write(c)
