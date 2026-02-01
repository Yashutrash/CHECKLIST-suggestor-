import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import random

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

# Parameters
NUM_RECORDS = 5000
INSPECTION_TYPES = ['Daily Safety Check', 'Quarterly HVAC Audit', 'Annual Fire Safety', 'Monthly Electrical']
LOCATIONS = ['Old Building', 'New Building', 'Warehouse', 'Office A', 'Office B']
CHECKLIST_ITEMS = [
    ('Check fire extinguisher pressure', 'safety'),
    ('Inspect HVAC filter', 'hvac'),
    ('Test emergency lights', 'safety'),
    ('Check electrical panel', 'electrical'),
    ('Review exit signs', 'safety'),
    ('Inspect roof access', 'general'),
    ('Check CO2 detectors', 'safety'),
    ('Inspect wiring', 'electrical'),
    ('Check thermostat', 'hvac'),
    ('Test smoke alarms', 'safety'),
]
OUTCOMES = ['PASS', 'FAIL', 'N/A']
COMMENTS_FAIL = [
    'Needs replacement',
    'Not accessible',
    'Expired tag',
    'Low pressure',
    'Obstructed',
    'Wiring exposed',
    'Filter dirty',
    'Battery low',
    'Sign missing',
    'Alarm not working',
]
COMMENTS_PASS = [
    'All good',
    'Checked and working',
    'No issues found',
    'Compliant',
    'Operational',
]

def generate_mock_data(num_records=NUM_RECORDS):
    records = []
    start_date = datetime(2022, 1, 1)
    for i in range(num_records):
        inspection_id = i // 10  # 10 items per inspection
        location_id = random.choice(range(len(LOCATIONS)))
        inspection_type = random.choice(INSPECTION_TYPES)
        checklist_item_id = i % len(CHECKLIST_ITEMS)
        checklist_item_text, category = CHECKLIST_ITEMS[checklist_item_id]
        # Embed some patterns: HVAC filter fails more in Old Building during Quarterly HVAC Audit
        if (checklist_item_text == 'Inspect HVAC filter' and
            LOCATIONS[location_id] == 'Old Building' and
            inspection_type == 'Quarterly HVAC Audit'):
            outcome = np.random.choice(['FAIL', 'PASS'], p=[0.7, 0.3])
        # Fire extinguisher fails more in Old Building
        elif (checklist_item_text == 'Check fire extinguisher pressure' and
              LOCATIONS[location_id] == 'Old Building'):
            outcome = np.random.choice(['FAIL', 'PASS'], p=[0.5, 0.5])
        else:
            outcome = np.random.choice(OUTCOMES, p=[0.1, 0.85, 0.05])
        if outcome == 'FAIL':
            comment = random.choice(COMMENTS_FAIL)
        elif outcome == 'PASS':
            comment = random.choice(COMMENTS_PASS)
        else:
            comment = ''
        timestamp = start_date + timedelta(days=random.randint(0, 730))
        records.append({
            'inspection_id': inspection_id,
            'location_id': location_id,
            'location': LOCATIONS[location_id],
            'inspection_type': inspection_type,
            'checklist_item_id': checklist_item_id,
            'checklist_item_text': checklist_item_text,
            'category': category,
            'outcome': outcome,
            'comments': comment,
            'timestamp': timestamp.strftime('%Y-%m-%d'),
        })
    df = pd.DataFrame(records)
    df.to_csv('data/mock_inspection_data.csv', index=False)
    print(f"Generated {len(df)} records in data/mock_inspection_data.csv")

if __name__ == '__main__':
    generate_mock_data() 