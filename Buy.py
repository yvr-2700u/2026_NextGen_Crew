"""Builds "Buy Now" links for a product name.

Zepto is the primary store. Since Zepto (and most quick-commerce apps)
don't expose a public search API, these are just search-page deep links —
if the product isn't listed there, the same row offers a couple of other
popular stores to try, plus a plain Google search as a catch-all.
"""

from urllib.parse import quote_plus

STORES = [
    {"key": "zepto", "label": "Zepto", "url": "https://www.zepto.com/search?query={query}"},
    {"key": "blinkit", "label": "Blinkit", "url": "https://blinkit.com/s/?q={query}"},
    {"key": "instamart", "label": "Swiggy Instamart", "url": "https://www.swiggy.com/instamart/search?custom_back=true&query={query}"},
    {"key": "amazon", "label": "Amazon", "url": "https://www.amazon.in/s?k={query}"},
]

GOOGLE_SEARCH_URL = "https://www.google.com/search?q={query}"


def get_buy_links(product_name):
    """Returns [{'key','label','url'}, ...] — Zepto first, other stores as
    fallback in case Zepto doesn't have the product listed."""
    if not product_name or product_name in ("N/A", "—"):
        return []

    query = quote_plus(product_name)
    return [
        {"key": store["key"], "label": store["label"], "url": store["url"].format(query=query)}
        for store in STORES
    ]


def get_google_search_url(product_name):
    """Plain Google search link used by the 'Find Online' fallback."""
    if not product_name or product_name in ("N/A", "—"):
        return None
    return GOOGLE_SEARCH_URL.format(query=quote_plus(product_name))