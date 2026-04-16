import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = "https://api.inaturalist.org/v1/observations"

PLACE_ID = os.getenv("PLACE_ID", "").strip()
TAXON_ID = os.getenv("TAXON_ID", "").strip()
def build_url(page: int) -> str:
    params = {
        "page": page,
        "per_page": PER_PAGE,
        "order_by": "observed_on",
        "order": "desc",
        "geo": "true",
    }

    if PLACE_ID:
        params["place_id"] = PLACE_ID
    if TAXON_ID:
        params["taxon_id"] = TAXON_ID
    if QUALITY_GRADE:
        params["quality_grade"] = QUALITY_GRADE

    # iNat expects repeated iconic_taxa[] params, not one comma string
    if ICONIC_TAXA:
        taxa = [t.strip() for t in ICONIC_TAXA.split(",") if t.strip()]
        params["iconic_taxa[]"] = taxa

    # helpful filters
    params["has[]"] = ["geo", "photos"]

    return f"{BASE_URL}?{urllib.parse.urlencode(params, doseq=True)}"
QUALITY_GRADE = os.getenv("QUALITY_GRADE", "").strip()
PER_PAGE = int(os.getenv("PER_PAGE", "200"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "10"))

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "inat-observations.geojson"


def fetch_json(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Ling-uMap-iNat-bridge/1.0"
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_url(page: int) -> str:
    params = {
        "page": page,
        "per_page": PER_PAGE,
        "order_by": "observed_on",
        "order": "desc",
        "geo": "true",
    }

    if PLACE_ID:
        params["place_id"] = PLACE_ID
    if TAXON_ID:
        params["taxon_id"] = TAXON_ID
    if ICONIC_TAXA:
        params["iconic_taxa"] = ICONIC_TAXA
    if QUALITY_GRADE:
        params["quality_grade"] = QUALITY_GRADE

    return f"{BASE_URL}?{urllib.parse.urlencode(params)}"


def feature_from_obs(obs: dict):
    geom = obs.get("geojson")
    if not geom:
        lat = obs.get("latitude")
        lng = obs.get("longitude")
        if lat is None or lng is None:
            return None
        geom = {"type": "Point", "coordinates": [lng, lat]}

    taxon = obs.get("taxon") or {}
    user = obs.get("user") or {}
    photos = obs.get("photos") or []

    image_url = None
    if photos:
        image_url = photos[0].get("url")
        if image_url:
            image_url = image_url.replace("square", "medium")

    props = {
        "id": obs.get("id"),
        "uri": obs.get("uri"),
        "observed_on": obs.get("observed_on"),
        "time_observed_at": obs.get("time_observed_at"),
        "species_guess": obs.get("species_guess"),
        "place_guess": obs.get("place_guess"),
        "quality_grade": obs.get("quality_grade"),
        "iconic_taxon_name": taxon.get("iconic_taxon_name"),
        "taxon_name": taxon.get("name"),
        "preferred_common_name": taxon.get("preferred_common_name"),
        "user_login": user.get("login"),
        "observations_url": obs.get("uri"),
        "image_url": image_url,
    }

    return {
        "type": "Feature",
        "geometry": geom,
        "properties": props,
    }


def main():
    features = []

    for page in range(1, MAX_PAGES + 1):
        url = build_url(page)
        data = fetch_json(url)
        results = data.get("results", [])

        if not results:
            break

        for obs in results:
            feat = feature_from_obs(obs)
            if feat:
                features.append(feat)

        if len(results) < PER_PAGE:
            break

        time.sleep(1)

    fc = {
        "type": "FeatureCollection",
        "features": features,
    }

    OUTPUT_FILE.write_text(json.dumps(fc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(features)} features to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
