from django.contrib import sitemaps
from django.urls import reverse

class StaticViewSitemap(sitemaps.Sitemap):
    priority = 1
    changefreq = 'monthly'

    def items(self):
        return ['home', 'method', 'get_reference', 'impressum', 'datenschutz']

    def location(self, item):
        return reverse(item)