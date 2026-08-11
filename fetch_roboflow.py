import urllib.request
import json

api_key = "6DqzyxObhbjKuobJhfjX"
workspace = "tien-anh-vu-5dm0q"

# Try to get workspace info to find projects
url = f"https://api.roboflow.com/{workspace}?api_key={api_key}"
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f"Error: {e}")
