import os
import secrets
import logging
import requests
from datetime import datetime, timedelta, time
from urllib.parse import urlencode
from collections import defaultdict, Counter
from typing import Dict, Any

from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpRequest
from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from .models import SpotifyAccount, SpotifyPlayEvent
from .spotify_api import SpotifyAPIClient, SpotifyAPIError, SpotifyTokenExpiredError
from accounts.models import User

logger = logging.getLogger(__name__)

# Spotify OAuth Configuration
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = os.getenv(
    "SPOTIFY_REDIRECT_URI", "http://localhost:8000/api/spotify/callback/"
)
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

# CSRF State token storage
OAUTH_STATE_KEY = "spotify_oauth_state"


# ============================================================================
# 1. OAUTH ENDPOINTS
# ============================================================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def spotify_connect(request: Request) -> Response:
    """
    Initiates Spotify OAuth flow.
    Generates state token and returns authorization URL.
    """
    # Generate a random state token for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state in session (expires after 10 minutes)
    request.session[OAUTH_STATE_KEY] = state
    request.session.set_expiry(600)  # 10 minutes

    # Build authorization URL
    params = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "state": state,
        "scope": " ".join(
            [
                "user-read-recently-played",
                "user-top-read",
            ]
        ),
    }

    auth_url = f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"

    return Response(
        {
            "authorization_url": auth_url,
            "message": "Redirect user to this URL to authorize Spotify access",
        }
    )


@require_http_methods(["GET"])
@csrf_exempt  # Spotify callback doesn't have CSRF token
def spotify_callback(request: HttpRequest) -> JsonResponse:
    """
    Handles Spotify OAuth callback.
    Exchanges authorization code for access token and stores user credentials.
    """
    # Extract authorization code and state
    code = request.GET.get("code")
    state = request.GET.get("state")
    error = request.GET.get("error")

    # Handle errors
    if error:
        return JsonResponse(
            {"status": "error", "message": f"Spotify authorization failed: {error}"},
            status=400,
        )

    if not code:
        return JsonResponse(
            {"status": "error", "message": "Missing authorization code"}, status=400
        )

    # Verify state token (CSRF protection)
    stored_state = request.session.get(OAUTH_STATE_KEY)
    if not state or state != stored_state:
        return JsonResponse(
            {
                "status": "error",
                "message": "Invalid state token - possible CSRF attack",
            },
            status=403,
        )

    # Clean up state from session
    del request.session[OAUTH_STATE_KEY]

    # Get user from query parameter or session
    user_id = request.GET.get("user_id")
    if not user_id and request.user.is_authenticated:
        user_id = request.user.id

    if not user_id:
        return JsonResponse(
            {
                "status": "error",
                "message": "Unable to determine user - please provide user_id parameter",
            },
            status=400,
        )

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "User not found"}, status=404
        )

    # Exchange code for tokens
    try:
        token_response = requests.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": SPOTIFY_REDIRECT_URI,
                "client_id": SPOTIFY_CLIENT_ID,
                "client_secret": SPOTIFY_CLIENT_SECRET,
            },
        )
        token_response.raise_for_status()
        token_data = token_response.json()
    except requests.RequestException as e:
        return JsonResponse(
            {
                "status": "error",
                "message": f"Failed to exchange authorization code: {str(e)}",
            },
            status=500,
        )

    # Extract token information
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour
    scope = token_data.get("scope", "")

    # Get user profile from Spotify
    try:
        profile_response = requests.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        profile_response.raise_for_status()
        profile_data = profile_response.json()
    except requests.RequestException as e:
        return JsonResponse(
            {
                "status": "error",
                "message": f"Failed to fetch Spotify user profile: {str(e)}",
            },
            status=500,
        )

    spotify_user_id = profile_data.get("id")

    # Calculate token expiration time
    expires_at = timezone.now() + timedelta(seconds=expires_in)

    # Store or update SpotifyAccount
    spotify_account, created = SpotifyAccount.objects.update_or_create(
        user=user,
        defaults={
            "spotify_user_id": spotify_user_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "scope": scope,
        },
    )

    return JsonResponse(
        {
            "status": "success",
            "message": "Spotify account connected successfully",
            "spotify_user_id": spotify_user_id,
            "user_id": user.id,
        }
    )


# ============================================================================
# 2. SYNC ENDPOINT (Ingest Recently Played)
# ============================================================================


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sync_recently_played(request: Request) -> Response:
    """
    Syncs user's recently played tracks from Spotify and stores in SpotifyPlayEvent.

    Query params:
    - limit (int, default 50): Number of recent plays to sync

    Returns:
    {
        "status": "success",
        "inserted": int,
        "skipped": int,
        "total": int,
        "message": str
    }
    """
    user = request.user

    # Check if user has Spotify connected
    try:
        spotify_account = SpotifyAccount.objects.get(user=user)
    except SpotifyAccount.DoesNotExist:
        return Response(
            {
                "status": "error",
                "message": "Spotify account not connected. Please authorize first.",
            },
            status=400,
        )

    # Initialize API client
    try:
        client = SpotifyAPIClient(user)
    except ValueError as e:
        return Response({"status": "error", "message": str(e)}, status=400)

    # Get limit from query params
    limit = int(request.query_params.get("limit", 50))
    limit = min(limit, 50)  # Spotify API max is 50 per request

    # Fetch recently played
    try:
        logger.info(f"Fetching recently played for user {user.username}")
        recently_played = client.get(
            "/me/player/recently_played", params={"limit": limit}
        )
    except SpotifyTokenExpiredError:
        return Response(
            {
                "status": "error",
                "message": "Your Spotify token has expired or been revoked. Please reconnect.",
            },
            status=401,
        )
    except SpotifyAPIError as e:
        return Response(
            {
                "status": "error",
                "message": f"Failed to fetch recently played: {str(e)}",
            },
            status=500,
        )

    # Process and upsert plays
    inserted = 0
    skipped = 0

    items = recently_played.get("items", [])
    logger.info(f"Processing {len(items)} recently played tracks")

    for item in items:
        try:
            # Extract play info
            track = item.get("track", {})
            played_at_str = item.get("played_at")
            played_at = datetime.fromisoformat(played_at_str.replace("Z", "+00:00"))

            track_id = track.get("id")
            track_name = track.get("name")
            album = track.get("album", {})
            album_id = album.get("id", "")
            album_name = album.get("name", "")

            # Extract artist info
            artists = track.get("artists", [])
            artist_ids = [a.get("id") for a in artists if a.get("id")]
            artist_names = [a.get("name") for a in artists if a.get("name")]

            # Extract context
            context = item.get("context", {})
            context_type = context.get("type", "") if context else ""
            context_uri = context.get("uri", "") if context else ""

            # Upsert play event
            play_event, created = SpotifyPlayEvent.objects.update_or_create(
                user=user,
                track_id=track_id,
                played_at=played_at,
                defaults={
                    "track_name": track_name,
                    "artist_ids": artist_ids,
                    "artist_names": artist_names,
                    "album_id": album_id,
                    "album_name": album_name,
                    "context_type": context_type,
                    "context_uri": context_uri,
                    "raw_payload": item,
                },
            )

            if created:
                inserted += 1
            else:
                skipped += 1

        except Exception as e:
            logger.error(f"Error processing play event: {e}")
            skipped += 1

    return Response(
        {
            "status": "success",
            "inserted": inserted,
            "skipped": skipped,
            "total": inserted + skipped,
            "message": f"Synced {inserted} new plays, {skipped} already existed",
        }
    )


# ============================================================================
# 3. DASHBOARD ENDPOINTS
# ============================================================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_summary(request: Request) -> Response:
    """
    Returns dashboard summary: streaks, totals, new-vs-repeat ratio.

    Query params:
    - days (int, default 30): Time window in days

    Returns:
    {
        "total_plays": int,
        "unique_tracks": int,
        "unique_artists": int,
        "new_vs_repeat": {
            "new": int,
            "repeat": int,
            "ratio": float (new/total)
        },
        "current_streak": int (consecutive days listened),
        "top_played": [
            {"track_name": str, "artist_names": list, "count": int},
            ...
        ]
    }
    """
    user = request.user
    days = int(request.query_params.get("days", 30))
    cutoff = timezone.now() - timedelta(days=days)

    # Get plays in time window
    plays = SpotifyPlayEvent.objects.filter(user=user, played_at__gte=cutoff)

    total_plays = plays.count()
    unique_tracks = plays.values("track_id").distinct().count()
    unique_artists = 0
    for play in plays:
        unique_artists += len(set(play.artist_ids))
    unique_artists = len(set(aid for play in plays for aid in play.artist_ids))

    # New vs Repeat
    track_counts = plays.values("track_id").annotate(count=Count("track_id"))
    new_count = sum(1 for tc in track_counts if tc["count"] == 1)
    repeat_count = total_plays - new_count
    new_vs_repeat_ratio = new_count / total_plays if total_plays > 0 else 0

    # Current streak (consecutive days listened)
    current_streak = _calculate_streak(user, cutoff)

    # Top played tracks
    top_played = (
        plays.values("track_id", "track_name", "artist_names")
        .annotate(count=Count("track_id"))
        .order_by("-count")[:5]
    )

    return Response(
        {
            "summary": {
                "total_plays": total_plays,
                "unique_tracks": unique_tracks,
                "unique_artists": unique_artists,
                "days_window": days,
            },
            "new_vs_repeat": {
                "new": new_count,
                "repeat": repeat_count,
                "ratio": round(new_vs_repeat_ratio, 2),
            },
            "current_streak": current_streak,
            "top_played": [
                {
                    "track_name": t["track_name"],
                    "artist_names": t["artist_names"],
                    "count": t["count"],
                }
                for t in top_played
            ],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_heatmap(request: Request) -> Response:
    """
    Returns time-of-day "rhythm" heatmap: 7×24 grid (day × hour).

    Query params:
    - days (int, default 30): Time window in days

    Returns:
    {
        "heatmap": [
            [0, 0, 1, 2, ...],  // Monday hour 0-23
            [1, 2, 3, 4, ...],  // Tuesday
            ...
            [5, 4, 3, 2, ...]   // Sunday
        ],
        "day_labels": ["Mon", "Tue", ...],
        "hour_labels": [0, 1, 2, ..., 23]
    }
    """
    user = request.user
    days = int(request.query_params.get("days", 30))
    cutoff = timezone.now() - timedelta(days=days)

    # Initialize 7x24 grid
    heatmap = [[0 for _ in range(24)] for _ in range(7)]

    # Fetch plays and bin by day-of-week and hour
    plays = SpotifyPlayEvent.objects.filter(user=user, played_at__gte=cutoff)

    for play in plays:
        # Convert to user's timezone if available
        played_at = play.played_at
        if timezone.is_aware(played_at):
            # Assuming UTC, convert to user timezone
            played_at = played_at.astimezone(timezone.get_default_timezone())

        day_of_week = played_at.weekday()  # 0=Monday, 6=Sunday
        hour = played_at.hour
        heatmap[day_of_week][hour] += 1

    return Response(
        {
            "heatmap": heatmap,
            "day_labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "hour_labels": list(range(24)),
            "days_window": days,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_top(request: Request) -> Response:
    """
    Returns top tracks (from DB) and optionally from Spotify (short/medium/long term).

    Query params:
    - range (str, default "short_term"): "short_term" (4 weeks), "medium_term" (6 months), "long_term" (all)
    - limit (int, default 10): Number of results

    Returns:
    {
        "db_top": [{"track_name": str, "artist_names": list, "count": int}],
        "spotify_top": [{"name": str, "artists": list, "popularity": int}]  // if Spotify endpoint called
    }
    """
    user = request.user
    range_param = request.query_params.get("range", "short_term")
    limit = int(request.query_params.get("limit", 10))

    # Validate range
    if range_param not in ["short_term", "medium_term", "long_term"]:
        return Response(
            {
                "status": "error",
                "message": "Invalid range. Use: short_term, medium_term, or long_term",
            },
            status=400,
        )

    # Get DB top (based on play count in last 30 days)
    cutoff = timezone.now() - timedelta(days=30)
    db_plays = (
        SpotifyPlayEvent.objects.filter(user=user, played_at__gte=cutoff)
        .values("track_id", "track_name", "artist_names")
        .annotate(count=Count("track_id"))
        .order_by("-count")[:limit]
    )

    db_top = [
        {
            "track_name": p["track_name"],
            "artist_names": p["artist_names"],
            "count": p["count"],
        }
        for p in db_plays
    ]

    # Get Spotify top (if account connected)
    spotify_top = []
    try:
        client = SpotifyAPIClient(user)
        spotify_response = client.get(
            "/me/top/tracks", params={"time_range": range_param, "limit": limit}
        )
        spotify_top = [
            {
                "name": t["name"],
                "artists": [a["name"] for a in t.get("artists", [])],
                "popularity": t.get("popularity", 0),
            }
            for t in spotify_response.get("items", [])
        ]
    except (SpotifyTokenExpiredError, SpotifyAPIError, ValueError) as e:
        logger.warning(f"Failed to fetch Spotify top: {e}")

    return Response(
        {
            "db_top": db_top,
            "spotify_top": spotify_top,
            "range": range_param,
        }
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _calculate_streak(user: User, cutoff: datetime) -> int:
    """
    Calculate current listening streak (consecutive days listened).
    """
    # Get unique days user listened in window
    plays = SpotifyPlayEvent.objects.filter(
        user=user, played_at__gte=cutoff
    ).values_list("played_at", flat=True)

    if not plays:
        return 0

    # Get unique dates
    dates = set()
    for play_dt in plays:
        if timezone.is_aware(play_dt):
            play_dt = play_dt.astimezone(timezone.get_default_timezone())
        dates.add(play_dt.date())

    # Sort dates
    sorted_dates = sorted(list(dates), reverse=True)

    # Count consecutive days from today
    streak = 0
    today = timezone.now().date()

    for i, date in enumerate(sorted_dates):
        expected_date = today - timedelta(days=i)
        if date == expected_date:
            streak += 1
        else:
            break

    return streak
