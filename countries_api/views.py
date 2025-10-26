from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from django.http import FileResponse, Http404
import threading
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from decimal import Decimal

from .models import Country, RefreshMetadata
from .serializers import (
    CountrySerializer,
    CountryListSerializer,
    StatusResponseSerializer,
    ErrorResponseSerializer,
    RefreshResponseSerializer
)
from .utils import (
    fetch_countries_data,
    fetch_exchange_rates,
    calculate_estimated_gdp,
    extract_currency_code,
    generate_summary_image,
    get_summary_image_path,
    ExternalAPIError
)


@swagger_auto_schema(
    method='post',
    operation_description='Fetch all countries and exchange rates, then cache them in the database',
    responses={
        200: RefreshResponseSerializer,
        503: ErrorResponseSerializer
    },
    tags=['Countries']
)
@api_view(['POST'])
def refresh_countries(request):
    """
    POST /countries/refresh
    Fetch all countries and exchange rates, then cache them in the database
    """
    # Start background refresh task and return immediately (202 Accepted)
    try:
        started_at = timezone.now()

        # create a metadata entry indicating refresh started
        RefreshMetadata.objects.create(
            total_countries=Country.objects.count(),
            last_refreshed_at=started_at,
            refresh_status='in_progress'
        )

        def chunks(iterable, size=100):
            for i in range(0, len(iterable), size):
                yield iterable[i:i + size]

        def perform_refresh(timestamp):
            try:
                # fetch external data inside background worker so main request never blocks on external APIs
                try:
                    data = fetch_countries_data()
                    rates = fetch_exchange_rates()
                    print(data)
                    # print(rates)
                except ExternalAPIError:
                    # Record failure metadata and exit
                    RefreshMetadata.objects.create(
                        total_countries=Country.objects.count(),
                        last_refreshed_at=timezone.now(),
                        refresh_status='failed'
                    )
                    return

                batch_size = 100

                # Build a lookup of existing countries by lowercased name
                existing_qs = Country.objects.all()
                existing_map = {c.name.lower(): c for c in existing_qs}

                to_create = []
                to_update = []

                for chunk in chunks(data, batch_size):
                    to_create.clear()
                    to_update.clear()

                    for country_data in chunk:
                        name = (country_data.get('name') or '').strip()
                        if not name:
                            continue

                        capital = country_data.get('capital', None)
                        region = country_data.get('region', None)
                        population = country_data.get('population', 0)
                        flag_url = country_data.get('flag', None)
                        currencies = country_data.get('currencies', [])

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

                        # prepare instance
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
                                last_refreshed_at=timestamp
                            )
                            to_create.append(inst)

                    # Bulk create and bulk update for this chunk
                    if to_create:
                        Country.objects.bulk_create(to_create, batch_size=len(to_create))
                        # add newly created instances to existing_map so later chunks can update them if needed
                        for c in to_create:
                            existing_map[c.name.lower()] = c

                    if to_update:
                        Country.objects.bulk_update(
                            to_update,
                            ['capital', 'region', 'population', 'currency_code', 'exchange_rate', 'estimated_gdp', 'flag_url', 'last_refreshed_at'],
                            batch_size=len(to_update)
                        )

                # Mark refresh success
                total_countries = Country.objects.count()
                RefreshMetadata.objects.create(
                    total_countries=total_countries,
                    last_refreshed_at=timestamp,
                    refresh_status='success'
                )

                # Generate summary image
                top_5_countries = Country.objects.filter(
                    estimated_gdp__isnull=False
                ).order_by('-estimated_gdp')[:5].values('name', 'estimated_gdp')

                generate_summary_image(
                    total_countries=total_countries,
                    top_5_countries=list(top_5_countries),
                    timestamp=timestamp
                )

            except Exception as exc:
                # record failure
                RefreshMetadata.objects.create(
                    total_countries=Country.objects.count(),
                    last_refreshed_at=timezone.now(),
                    refresh_status='failed'
                )

        # Start background thread
        thread = threading.Thread(target=perform_refresh, args=(started_at,), daemon=True)
        thread.start()

        return Response({
            'message': 'Refresh started',
            'started_at': started_at.strftime('%Y-%m-%dT%H:%M:%SZ')
        }, status=status.HTTP_200_OK)

    except ExternalAPIError as e:
        return Response({
            'error': 'External data source unavailable',
            'details': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        return Response({
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    operation_description='Get all countries from the database with optional filters and sorting',
    manual_parameters=[
        openapi.Parameter(
            'region',
            openapi.IN_QUERY,
            description='Filter by region (e.g., Africa, Europe)',
            type=openapi.TYPE_STRING
        ),
        openapi.Parameter(
            'currency',
            openapi.IN_QUERY,
            description='Filter by currency code (e.g., NGN, USD)',
            type=openapi.TYPE_STRING
        ),
        openapi.Parameter(
            'sort',
            openapi.IN_QUERY,
            description='Sort by gdp_desc, gdp_asc, population_desc, population_asc, name_asc, name_desc',
            type=openapi.TYPE_STRING
        ),
    ],
    responses={
        200: CountryListSerializer(many=True),
        400: ErrorResponseSerializer
    },
    tags=['Countries']
)
@api_view(['GET'])
def get_countries(request):
    """
    GET /countries
    Get all countries from the database with optional filters and sorting
    """
    try:
        queryset = Country.objects.all()

        # Filter by region
        region = request.query_params.get('region', None)
        if region:
            queryset = queryset.filter(region__iexact=region)

        # Filter by currency
        currency = request.query_params.get('currency', None)
        if currency:
            queryset = queryset.filter(currency_code__iexact=currency)

        # Sorting
        sort_param = request.query_params.get('sort', None)
        if sort_param:
            if sort_param == 'gdp_desc':
                queryset = queryset.exclude(estimated_gdp__isnull=True).order_by('-estimated_gdp')
            elif sort_param == 'gdp_asc':
                queryset = queryset.exclude(estimated_gdp__isnull=True).order_by('estimated_gdp')
            elif sort_param == 'population_desc':
                queryset = queryset.order_by('-population')
            elif sort_param == 'population_asc':
                queryset = queryset.order_by('population')
            elif sort_param == 'name_asc':
                queryset = queryset.order_by('name')
            elif sort_param == 'name_desc':
                queryset = queryset.order_by('-name')

        serializer = CountryListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    operation_description='Get a single country by name',
    responses={
        200: CountrySerializer,
        404: ErrorResponseSerializer
    },
    tags=['Countries']
)
@api_view(['GET'])
def get_country_by_name(request, name):
    """
    GET /countries/:name
    Get one country by name
    """
    try:
        country = Country.objects.get(name__iexact=name)
        serializer = CountrySerializer(country)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Country.DoesNotExist:
        return Response({
            'error': 'Country not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='delete',
    operation_description='Delete a country record by name',
    responses={
        204: openapi.Response(
            description='Country deleted successfully',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        404: ErrorResponseSerializer
    },
    tags=['Countries']
)
@api_view(['GET', 'DELETE'])
def delete_country(request, name):
    """
    DELETE /countries/:name
    Delete a country record
    """
    if request.method == 'GET':
        try:
            country = Country.objects.get(name__iexact=name)
            serializer = CountrySerializer(country)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Country.DoesNotExist:
            return Response({
                'error': 'Country not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Internal server error',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # DELETE
    try:
        country = Country.objects.get(name__iexact=name)
        country.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except Country.DoesNotExist:
        return Response({
            'error': 'Country not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    operation_description='Show total countries and last refresh timestamp',
    responses={
        200: StatusResponseSerializer,
        404: ErrorResponseSerializer
    },
    tags=['Countries']
)
@api_view(['GET'])
def get_status(request):
    """
    GET /status
    Show total countries and last refresh timestamp
    """
    try:
        total_countries = Country.objects.count()

        # Get last refresh metadata
        try:
            last_refresh = RefreshMetadata.objects.latest('last_refreshed_at')
            last_refreshed_at = last_refresh.last_refreshed_at.strftime('%Y-%m-%dT%H:%M:%SZ')
        except RefreshMetadata.DoesNotExist:
            last_refreshed_at = None

        return Response({
            'total_countries': total_countries,
            'last_refreshed_at': last_refreshed_at
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    operation_description='Serve the generated summary image',
    responses={
        200: openapi.Response(
            description='Summary image',
            schema=openapi.Schema(
                type=openapi.TYPE_FILE
            )
        ),
        404: ErrorResponseSerializer
    },
    tags=['Countries']
)
@api_view(['GET'])
def get_summary_image(request):
    """
    GET /countries/image
    Serve the generated summary image
    """
    try:
        image_path = get_summary_image_path()

        if image_path is None:
            return Response({
                'error': 'Summary image not found'
            }, status=status.HTTP_404_NOT_FOUND)

        return FileResponse(
            open(image_path, 'rb'),
            content_type='image/png',
            as_attachment=False,
            filename='summary.png'
        )

    except Exception as e:
        return Response({
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
