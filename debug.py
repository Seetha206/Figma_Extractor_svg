import os
from dotenv import load_dotenv

# Try to load .env file
print("=== Environment Variable Debug ===")

# Check if .env file exists
env_files = ['.env', '.env.']
env_found = False

for env_file in env_files:
    if os.path.exists(env_file):
        print(f"✅ Found {env_file}")
        load_dotenv(env_file)
        env_found = True
        break

if not env_found:
    print("❌ No .env file found")
    print("Current directory:", os.getcwd())
    print("Files in directory:", os.listdir('.'))

# Check environment variables
figma_token = os.getenv('FIGMA_API_TOKEN')
do_access = os.getenv('DO_ACCESS_KEY')
do_secret = os.getenv('DO_SECRET_KEY')
do_region = os.getenv('DO_REGION')
do_space = os.getenv('DO_SPACE_NAME')

print("\n=== Environment Variables ===")
print(f"FIGMA_API_TOKEN: {'✅ Set' if figma_token else '❌ Not set'}")
if figma_token:
    print(f"  Length: {len(figma_token)} characters")
    print(f"  Starts with: {figma_token[:8]}...")
    print(f"  Ends with: ...{figma_token[-4:]}")

print(f"DO_ACCESS_KEY: {'✅ Set' if do_access else '❌ Not set'}")
print(f"DO_SECRET_KEY: {'✅ Set' if do_secret else '❌ Not set'}")
print(f"DO_REGION: {do_region or '❌ Not set'}")
print(f"DO_SPACE_NAME: {do_space or '❌ Not set'}")

print("\n=== Figma Token Test ===")
if figma_token:
    import requests
    headers = {
        'X-Figma-Token': figma_token,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get('https://api.figma.com/v1/me', headers=headers, timeout=10)
        print(f"API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"✅ Token is valid!")
            print(f"User: {user_info.get('email', 'Unknown')}")
        elif response.status_code == 403:
            print("❌ 403 Forbidden - Token is invalid or expired")
            print("Response:", response.text[:200])
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print("Response:", response.text[:200])
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
else:
    print("❌ No token to test")