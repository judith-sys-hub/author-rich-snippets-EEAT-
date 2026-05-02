_PUBLISHER = {
    "@type": "NewsMediaOrganization",
    "@id": "https://www.kleinezeitung.at",
    "name": "Kleine Zeitung",
}


def _set_if(node: dict, key: str, value) -> None:
    if value is not None:
        node[key] = value


def render_jsonld(author_data: dict) -> dict:
    profile = author_data["profile"]
    profile_url = profile["profile_url"]

    person: dict = {"@type": "Person", "@id": profile_url}
    _set_if(person, "name", profile.get("name"))
    _set_if(person, "jobTitle", profile.get("title"))
    _set_if(person, "description", profile.get("bio_generated"))
    _set_if(person, "image", profile.get("photo_url"))
    person["url"] = profile_url
    person["worksFor"] = dict(_PUBLISHER)

    beats = (author_data.get("expertise") or {}).get("beats") or []
    if beats:
        person["knowsAbout"] = beats

    enrichment = author_data.get("enrichment") or {}
    social = enrichment.get("social_links") or {}
    same_as = [v for v in social.values() if v]
    wiki = enrichment.get("wikipedia_url")
    if wiki:
        same_as.append(wiki)
    if same_as:
        person["sameAs"] = same_as

    graph: list = [person]
    for article in author_data.get("articles") or []:
        node: dict = {
            "@type": "NewsArticle",
            "headline": article["title"],
            "url": article["url"],
            "datePublished": article["published_at"],
            "author": {"@id": profile_url},
            "publisher": dict(_PUBLISHER),
        }
        if article.get("section"):
            node["articleSection"] = article["section"]
        graph.append(node)

    return {"@context": "https://schema.org", "@graph": graph}