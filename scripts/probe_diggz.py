#!/usr/bin/env python3
import re
import urllib.request

URL = "https://raw.githubusercontent.com/nebulous42069/Omega/main/omega/zips/addons.xml"
data = urllib.request.urlopen(URL, timeout=30).read().decode("utf-8", errors="ignore")
for match in re.finditer(r'id="(plugin\.program\.[^"]+)"[^>]*name="([^"]*)"', data):
    addon_id, name = match.groups()
    if "program" in addon_id:
        print(addon_id, "-", name)
