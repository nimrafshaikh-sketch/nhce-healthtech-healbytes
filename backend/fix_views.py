import glob

for f in glob.glob('apps/*/views.py'):
    with open(f, 'r') as fp: c = fp.read()
    c = c.replace('doctor=self.request.user', 'doctor=self.request.user.doctor_profile')
    c = c.replace('doctor=request.user', 'doctor=request.user.doctor_profile')
    with open(f, 'w') as fp: fp.write(c)

f = 'apps/patients/tests/test_patients.py'
with open(f, 'r') as fp: c = fp.read()
c = c.replace('"name": "New Patient"', '"name": "New Patient", "date_of_birth": "1990-01-01"')
with open(f, 'w') as fp: fp.write(c)
