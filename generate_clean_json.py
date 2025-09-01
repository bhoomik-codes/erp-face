# generate_clean_fixture.py
import json
import os
import sys

# Define the path to your original dump file (the one that might have binary data or extra text).
# This should be the *initial* dump you made from SQLite, usually named 'initial_data.json'.
# Do NOT set this to 'initial_data_clean.json' as that file itself might be malformed from previous attempts.
original_fixture_path = 'initial_data.json'
clean_fixture_path = 'initial_data_final.json'

# List of models to EXCLUDE from the clean fixture
# These are typically models that contain binary data, session data, or auth-related data
# that are better recreated or handled separately.
EXCLUDE_MODELS = [
    'attendance_app.employee',  # We'll migrate this separately using migrate_employees.py
    'sessions.session',         # Session data can be problematic and is usually temporary
    'auth.permission',          # Django's permissions are recreated by migrate
    'contenttypes.contenttype', # Django's content types are recreated by migrate
    'admin.logentry',           # Admin logs are not essential for migration
    'auth.group',               # Groups can be recreated if needed
    'auth.user',                # CustomUser will be handled by createsuperuser
    'attendance_app.customuser', # Exclude your custom user model as well
]

print(f"Reading original fixture from: {original_fixture_path}")

try:
    # Read the file in binary mode to avoid UnicodeDecodeError on raw bytes
    with open(original_fixture_path, 'rb') as f:
        raw_content = f.read()

    # Try to find the start of the JSON array (the first '[')
    # This handles cases where there's leading non-JSON text (like "Loaded X face encodings from file.")
    json_start_index = raw_content.find(b'[')
    if json_start_index == -1:
        raise ValueError("Could not find the start of a JSON array ('[') in the file.")

    # --- IMPORTANT CHANGE HERE: Decode the content from UTF-16LE ---
    # Decode the JSON part from the found index, explicitly using 'utf-16-le'
    # This is based on the error message indicating the file's current encoding.
    json_content = raw_content[json_start_index:].decode('utf-16-le')

    # Load the JSON data
    data = json.loads(json_content)

    # Filter out the excluded models
    clean_data = [
        item for item in data
        if item.get('model') not in EXCLUDE_MODELS
    ]

    print(f"Filtered out models: {', '.join(EXCLUDE_MODELS)}")
    print(f"Original items: {len(data)}, Clean items: {len(clean_data)}")

    # Write the cleaned data to a new file with proper UTF-8 encoding
    with open(clean_fixture_path, 'w', encoding='utf-8') as f:
        json.dump(clean_data, f, indent=2)

    print(f"Successfully generated clean fixture at: {clean_fixture_path}")

except FileNotFoundError:
    print(f"Error: Original fixture file not found at '{original_fixture_path}'.")
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"Error decoding JSON from '{original_fixture_path}': {e}")
    print("Please ensure the file content after any leading non-JSON text is valid JSON.")
    sys.exit(1)
except ValueError as e:
    print(f"Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    sys.exit(1)
