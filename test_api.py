import requests
import re
from bs4 import BeautifulSoup
import logging

url = 'https://kovaaks.com/_next/static/chunks/app/kovaaks/leaderboards/page-b0c0ed916c44a3bd.js'
js = requests.get(url).text
apis = re.findall(r'https?://[^\"]*api[^\"]*', js)
print("APIs:", set(apis))
import sys
# Also check if there's any path like /api/...
paths = re.findall(r'\"/api/[^\"]*\"', js)
print("Paths:", set(paths))

# what else? Let's check the bundle for fetch calls
urls = re.findall(r'fetch\([\"\'\]?([^\)\"\'\]+)[\"\'\]?\)', js)
print("Fetch calls:", set(urls))
