import re

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

from exampapers.models import Course

DEFAULT_TIMEOUT = 10


class Command(BaseCommand):
    help = "Import a broad list of academic courses"

    def handle(self, *args, **kwargs):
        url = "https://en.wikipedia.org/wiki/List_of_academic_fields"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        soup = BeautifulSoup(response.content, "html.parser")

        # Use multiple strategies to find more course names
        sections = soup.select("div.div-col li a[href^='/wiki/']")

        course_names = set()
        for link in sections:
            text = link.get_text(strip=True)
            if text and len(text) > 2:
                # Remove parentheses (e.g. "Mathematics (Applied)" → "Mathematics")
                cleaned = re.sub(r"\s*\(.*?\)", "", text).strip()
                if cleaned:
                    course_names.add(cleaned)

        added = 0
        for name in course_names:
            if not Course.objects.filter(name__iexact=name).exists():
                Course.objects.create(name=name)
                added += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Imported {added} new courses"))
