#!/usr/bin/env python3

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - defensive fallback
    load_dotenv = None  # type: ignore[assignment]

from app.config import get_settings
from app.services.importer import ApiConfig, ProductClientFactory, detect_product_url

SUPPORTED_PLATFORMS = ("shopify", "woocommerce", "squarespace", "amazon", "aliexpress")
RAPIDAPI_PLATFORMS = {"amazon", "aliexpress"}


def _normalize_url(url: str) -> str:
    normalized = (url or "").strip()
    if not normalized:
        raise ValueError("URL is required.")
    if not normalized.startswith(("http://", "https://")):
        normalized = f"https://{normalized}"
    return normalized


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch raw upstream importer payloads (pre-normalization) for all supported import platforms."
        )
    )
    parser.add_argument("--shopify-url", help="Shopify product URL")
    parser.add_argument("--woocommerce-url", help="WooCommerce product URL")
    parser.add_argument("--squarespace-url", help="Squarespace product URL")
    parser.add_argument("--amazon-url", help="Amazon product URL")
    parser.add_argument("--aliexpress-url", help="AliExpress product URL")
    parser.add_argument(
        "--output-dir",
        default="tmp/importer-raw-payloads",
        help="Directory where per-platform JSON payload files are written",
    )
    return parser.parse_args()


def _fetch_snapshot(*, platform: str, url: str, cfg: ApiConfig, factory: ProductClientFactory) -> dict:
    normalized_url = _normalize_url(url)
    detected = detect_product_url(normalized_url)
    detected_platform = str(detected.get("platform") or "")
    if detected_platform != platform:
        raise ValueError(
            f"URL platform mismatch for {platform}: detected={detected_platform or 'unknown'} url={normalized_url}"
        )
    if not detected.get("is_product"):
        raise ValueError(f"URL for {platform} is not recognized as a product URL: {normalized_url}")
    if platform in RAPIDAPI_PLATFORMS and not cfg.rapidapi_key:
        raise ValueError("RAPIDAPI_KEY is required for Amazon and AliExpress payload fetches.")

    client = factory.for_url(normalized_url)
    product = client.fetch_product(normalized_url)
    return {
        "platform": platform,
        "url": normalized_url,
        "detected": detected,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw": product.raw,
    }


def main() -> int:
    if load_dotenv is not None:
        load_dotenv()

    args = _args()
    settings = get_settings()
    cfg = ApiConfig(rapidapi_key=settings.rapidapi_key, amazon_country=settings.amazon_country)
    factory = ProductClientFactory(cfg)

    urls_by_platform: dict[str, str | None] = {
        "shopify": args.shopify_url,
        "woocommerce": args.woocommerce_url,
        "squarespace": args.squarespace_url,
        "amazon": args.amazon_url,
        "aliexpress": args.aliexpress_url,
    }
    requested = {platform: url for platform, url in urls_by_platform.items() if url}
    if not requested:
        print(
            "No platform URLs were provided. Pass at least one of: "
            "--shopify-url, --woocommerce-url, --squarespace-url, --amazon-url, --aliexpress-url",
            file=sys.stderr,
        )
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    errors: list[tuple[str, str]] = []
    for platform in SUPPORTED_PLATFORMS:
        platform_url = requested.get(platform)
        if not platform_url:
            print(f"[skip] {platform}: no URL provided")
            continue
        try:
            snapshot = _fetch_snapshot(
                platform=platform,
                url=platform_url,
                cfg=cfg,
                factory=factory,
            )
            destination = output_dir / f"{platform}.json"
            destination.write_text(
                json.dumps(snapshot, indent=2, ensure_ascii=False, default=str) + "\n",
                encoding="utf-8",
            )
            print(f"[ok] {platform}: {destination}")
        except Exception as exc:
            errors.append((platform, str(exc)))
            print(f"[error] {platform}: {exc}", file=sys.stderr)

    if errors:
        print("\nRaw payload fetch completed with errors:", file=sys.stderr)
        for platform, message in errors:
            print(f"- {platform}: {message}", file=sys.stderr)
        return 1

    print("\nRaw payload fetch completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
