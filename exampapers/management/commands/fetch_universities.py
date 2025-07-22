import requests
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from exampapers.models import School

CSV_URL = "https://raw.githubusercontent.com/Hipo/university-domains-list/master/world_universities_and_domains.json"
TARGET_COUNTRIES = {"United States", "Canada", "United Kingdom"}

DEFAULT_TIMEOUT = 10


class Command(BaseCommand):
    help = "Import universities from HipoLabs API for USA, Canada, and UK"

    def handle(self, *args, **kwargs):
        self.stdout.write("📥 Fetching university data...")

        try:
            response = requests.get(CSV_URL, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            universities = response.json()
        except requests.RequestException as e:
            self.stderr.write(f"❌ Error fetching data: {e}")
            return

        count = 0

        for uni in universities:
            country = uni["country"]
            if country not in TARGET_COUNTRIES:
                continue

            name = uni["name"]
            website = uni["web_pages"][0] if uni["web_pages"] else None
            slug = slugify(name)

            # Avoid duplicates
            if School.objects.filter(slug=slug).exists():
                continue

            School.objects.create(
                name=name, slug=slug, country=country, website=website, is_active=True
            )
            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"✅ Successfully imported {count} universities.")
        )
