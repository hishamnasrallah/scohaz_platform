import requests
import time

# Configuration
BASE_URL = 'http://localhost:8000/api'
# USERNAME = 'admin'  # Replace with your username
# PASSWORD = 'Amman!@#'  # Replace with your password
#
# # Login
# print("Logging in...")
# response = requests.post(f'{BASE_URL}/auth/login/', json={
#     'username': USERNAME,
#     'password': PASSWORD
# })
#
# if response.status_code != 200:
#     print(f"Login failed: {response.text}")
#     exit(1)
#
# tokens = response.json()
# headers = {'Authorization': f'Bearer {tokens["access"]}'}

# Get the Green App project
print("Finding Green App project...")
response = requests.get(f'{BASE_URL}/projects/flutter-projects/')
projects = response.json()['results']

green_app = None
for project in projects:
    if project['name'] == 'Green App':
        green_app = project
        break

if not green_app:
    print("Green App project not found!")
    exit(1)

print(f"Found project: {green_app['name']} (ID: {green_app['id']})")

# Create a build
print("Starting APK build...")
response = requests.post(
    f'{BASE_URL}/builds/',
    json={
        'project_id': green_app['id'],
        'build_type': 'release',
        'version_number': '1.0.0'
    },
    headers=headers
)

if response.status_code != 201:
    print(f"Failed to create build: {response.text}")
    exit(1)

build = response.json()
build_id = build['id']
print(f"Build created: #{build_id}")

# Monitor build progress
print("Building... (this may take a few minutes)")
while True:
    response = requests.get(f'{BASE_URL}/builds/{build_id}/', headers=headers)
    build = response.json()

    print(f"Status: {build['status_display']}")

    if build['status'] in ['success', 'failed', 'cancelled']:
        break

    time.sleep(5)

# Check final status
if build['status'] == 'success':
    print(f"\nBuild successful!")
    print(f"APK size: {build['apk_size']} bytes")

    # Download APK
    print("Downloading APK...")
    response = requests.get(
        f'{BASE_URL}/builds/{build_id}/download/',
        headers=headers
    )

    with open('green_app.apk', 'wb') as f:
        f.write(response.content)

    print("APK saved as: green_app.apk")
else:
    print(f"\nBuild failed: {build['error_message']}")

# Show build logs
response = requests.get(f'{BASE_URL}/builds/{build_id}/logs/', headers=headers)
logs = response.json()
print("\nBuild logs:")
for log in logs[-5:]:  # Last 5 logs
    print(f"[{log['level']}] {log['stage']}: {log['message']}")