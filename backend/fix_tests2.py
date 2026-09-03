import glob

for f in glob.glob('apps/*/tests/*.py'):
    with open(f, 'r') as fp:
        c = fp.read()
    
    # Fix self.other_doctor and NotMine
    c = c.replace('doctor=self.other_doctor)', 'doctor=self.other_doctor.doctor_profile)')
    c = c.replace('doctor=self.other_doctor, name="NotMine"', 'doctor=self.other_doctor.doctor_profile, name="NotMine", date_of_birth="1990-01-01"')
    
    # Fix test payloads missing fields
    c = c.replace('"full_name": "New Patient"', '"name": "New Patient", "date_of_birth": "1990-01-01"')
    c = c.replace('"full_name": "Jane Doe"', '"name": "Jane Doe", "date_of_birth": "1990-01-01"')
    c = c.replace('"full_name"', '"name"')
    c = c.replace('full_name=', 'name=')
    
    with open(f, 'w') as fp:
        fp.write(c)
