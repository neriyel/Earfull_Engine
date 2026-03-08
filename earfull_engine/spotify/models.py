from django.db import models
from django.utils import timezone
from datetime import timedelta
import os
import requests
from accounts.models import User


# ============================================================================
# MVP SCOPE: Lock features to prevent fighting deprecations
# ============================================================================
# ✅ INCLUDED:
#   - Recent listening timeline (last ~50 plays, daily grouping)
#   - Time-of-day heatmap (counts per hour × day)
#   - New vs repeat ratio (in your time window)
#   - Streaks (listened on X of last Y days)
#   - Top tracks/artists (short/medium/long term)
# ❌ NOT INCLUDED (but compatible later):
#   - Mood diary + mood heatmap overlay
#   - Full playlist/track/artist metadata cache
# ============================================================================


class SpotifyAccount(models.Model):
    """
    Stores the Spotify OAuth connection for a user.
    This is the record that answers: "Can we call Spotify on behalf of this user?"
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="spotify_account"
    )
    spotify_user_id = models.CharField(max_length=255, unique=True)
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    expires_at = models.DateTimeField()
    scope = models.TextField()  # Space-separated scopes granted
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Spotify Account"
        verbose_name_plural = "Spotify Accounts"

    def __str__(self):
        return f"{self.user.username} - Spotify Account"

    def is_token_expired(self):
        """Check if the access token has expired."""
        return timezone.now() >= self.expires_at

    def refresh_access_token(self):
        """
        Refreshes the Spotify access token using the refresh token.
        Returns True if successful, False otherwise.
        """
        if not self.refresh_token:
            return False

        try:
            token_url = "https://accounts.spotify.com/api/token"
            response = requests.post(
                token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": os.getenv("SPOTIFY_CLIENT_ID", ""),
                    "client_secret": os.getenv("SPOTIFY_CLIENT_SECRET", ""),
                },
            )
            response.raise_for_status()
            token_data = response.json()

            # Update tokens
            self.access_token = token_data.get("access_token")
            if "refresh_token" in token_data:
                self.refresh_token = token_data.get("refresh_token")

            expires_in = token_data.get("expires_in", 3600)
            self.expires_at = timezone.now() + timedelta(seconds=expires_in)
            self.save()
            return True
        except requests.RequestException:
            return False


class SpotifyPlayEvent(models.Model):
    """
    Event log of plays from Spotify "Recently Played" API.

    This is the primary data source for:
    - Recent listening timeline
    - Time-of-day heatmap
    - New vs repeat ratio
    - Streaks
    - Top tracks analysis

    Why: Recently Played only returns limited window (~50 last plays).
    We sync to build historical trends.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="spotify_play_events"
    )

    # Spotify IDs (stable identifiers)
    track_id = models.CharField(max_length=255, db_index=True)
    artist_ids = models.JSONField(default=list)  # List of Spotify artist IDs

    # Track metadata (denormalized for convenience)
    track_name = models.CharField(max_length=255)
    artist_names = models.JSONField(default=list)  # List of artist names
    album_id = models.CharField(max_length=255, blank=True)
    album_name = models.CharField(max_length=255, blank=True)

    # Play timing
    played_at = models.DateTimeField(db_index=True)  # When user played it

    # Optional context (what was playing: playlist, album, etc)
    context_type = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ("playlist", "Playlist"),
            ("album", "Album"),
            ("artist", "Artist"),
            ("user", "User (Liked)"),
        ],
    )
    context_uri = models.CharField(max_length=255, blank=True)  # Spotify URI

    # Debug / raw data
    raw_payload = models.JSONField(
        null=True, blank=True, help_text="Full Spotify API response"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Spotify Play Event"
        verbose_name_plural = "Spotify Play Events"
        # Prevent duplicate plays at exact same time
        unique_together = ("user", "track_id", "played_at")
        indexes = [
            models.Index(fields=["user", "played_at"]),
            models.Index(fields=["user", "track_id"]),
        ]
        ordering = ["-played_at"]

    def __str__(self):
        return f"{self.user.username} played {self.track_name} at {self.played_at}"
