import logging
from django.utils import timezone
from .models import Country, RefreshMetadata
from .utils import (
    fetch_countries_data,
    fetch_exchange_rates,
    calculate_estimated_gdp,
    extract_currency_code,
    generate_summary_image,
    ExternalAPIError,
)

logger = logging.getLogger(__name__)


def _chunks(iterable, size=100):
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


def refresh_countries_background(metadata_id: int, timestamp=None, batch_size: int = 100):
    """
    Background worker that refreshes countries and updates the provided
    RefreshMetadata record as it progresses.

    This function is intentionally independent from any task runner so it can
    be easily called from threads or Celery tasks.
    """
    if timestamp is None:
        timestamp = timezone.now()

    try:
        metadata = RefreshMetadata.objects.get(pk=metadata_id)
    except RefreshMetadata.DoesNotExist:
        logger.warning("RefreshMetadata id=%s not found, aborting refresh", metadata_id)
        return

    try:
        # indicate we've fetched countries
        metadata.refresh_status = 'in_progress'
        metadata.last_refreshed_at = timestamp
        metadata.save()

        # Fetch external data
        countries = fetch_countries_data()
        metadata.refresh_status = 'fetched_countries'
        metadata.save()

        rates = fetch_exchange_rates()
        metadata.refresh_status = 'fetched_rates'
        metadata.save()

    except ExternalAPIError as exc:
        logger.exception("External API failure during refresh: %s", exc)
        metadata.refresh_status = 'failed'
        metadata.last_refreshed_at = timezone.now()
        metadata.save()
        return

    try:
        metadata.refresh_status = 'processing'
        metadata.save()

        existing_qs = Country.objects.all()
        existing_map = {c.name.lower(): c for c in existing_qs}

        to_create = []
        to_update = []

        for chunk in _chunks(countries, batch_size):
            to_create.clear()
            to_update.clear()

            for country_data in chunk:
                name = (country_data.get('name') or '').strip()
                if not name:
                    continue

                capital = country_data.get('capital') or None
                region = country_data.get('region') or None
                population = country_data.get('population') or 0
                flag_url = country_data.get('flag') or None
                currencies = country_data.get('currencies') or []

                currency_code = extract_currency_code(currencies)

                exchange_rate = None
                estimated_gdp = None

                if currency_code:
                    rate_val = rates.get(currency_code) or rates.get(currency_code.upper())
                    if rate_val is not None:
                        try:
                            exchange_rate = float(rate_val)
                        except Exception:
                            exchange_rate = None
                        estimated_gdp = calculate_estimated_gdp(population, exchange_rate)

                key = name.lower()
                if key in existing_map:
                    inst = existing_map[key]
                    inst.capital = capital
                    inst.region = region
                    inst.population = population or 0
                    inst.currency_code = currency_code
                    inst.exchange_rate = exchange_rate
                    inst.estimated_gdp = estimated_gdp
                    inst.flag_url = flag_url
                    inst.last_refreshed_at = timestamp
                    to_update.append(inst)
                else:
                    inst = Country(
                        name=name,
                        capital=capital,
                        region=region,
                        population=population or 0,
                        currency_code=currency_code,
                        exchange_rate=exchange_rate,
                        estimated_gdp=estimated_gdp,
                        flag_url=flag_url,
                        last_refreshed_at=timestamp,
                    )
                    to_create.append(inst)

            if to_create:
                Country.objects.bulk_create(to_create, batch_size=len(to_create))
                for c in to_create:
                    existing_map[c.name.lower()] = c

            if to_update:
                Country.objects.bulk_update(
                    to_update,
                    ['capital', 'region', 'population', 'currency_code', 'exchange_rate', 'estimated_gdp', 'flag_url', 'last_refreshed_at'],
                    batch_size=len(to_update)
                )

        # success
        total_countries = Country.objects.count()
        metadata.total_countries = total_countries
        metadata.last_refreshed_at = timestamp
        metadata.refresh_status = 'success'
        metadata.save()

        # Generate image summarising results
        top_5 = Country.objects.filter(estimated_gdp__isnull=False).order_by('-estimated_gdp')[:5].values('name', 'estimated_gdp')
        try:
            generate_summary_image(total_countries=total_countries, top_5_countries=list(top_5), timestamp=timestamp)
        except Exception:
            logger.exception("Failed to generate summary image")

    except Exception as exc:
        logger.exception("Error during processing refresh: %s", exc)
        metadata.refresh_status = 'failed'
        metadata.last_refreshed_at = timezone.now()
        metadata.save()
