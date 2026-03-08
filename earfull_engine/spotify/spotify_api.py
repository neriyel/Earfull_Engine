"""
Spotify API utilities for authenticated requests.
Handles token refresh, rate limits, and error recovery.
"""

import logging
import time
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
from .models import SpotifyAccount

logger = logging.getLogger(__name__)


class SpotifyAPIError(Exception):
    """Base exception for Spotify API errors."""

    pass


class SpotifyTokenExpiredError(SpotifyAPIError):
    """Raised when token cannot be refreshed or is revoked."""

    pass


class SpotifyRateLimitError(SpotifyAPIError):
    """Raised when rate limit is exceeded after retries."""

    pass


class SpotifyAPIClient:
    """
    Helper class for making authenticated Spotify API requests.
    Handles token refresh, rate limits, and error recovery.
    """

    BASE_URL = "https://api.spotify.com/v1"
    REQUEST_TIMEOUT = 10  # seconds
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1  # seconds

    def __init__(self, user):
        """
        Initialize with a Django User object.

        Args:
            user: Django User instance

        Raises:
            ValueError: If user has no Spotify account connected
        """
        self.user = user
        self.account = None
        try:
            self.account = SpotifyAccount.objects.get(user=user)
        except SpotifyAccount.DoesNotExist:
            logger.error(
                f"User {user.username} does not have a Spotify account connected"
            )
            raise ValueError(
                f"User {user.username} does not have a Spotify account connected"
            )

    def _ensure_valid_token(self):
        """
        Refresh access token if expired.

        Raises:
            SpotifyTokenExpiredError: If token refresh fails or token is revoked
        """
        if self.account.is_token_expired():
            logger.info(
                f"Token expired for user {self.user.username}, attempting refresh"
            )
            success = self.account.refresh_access_token()
            if not success:
                logger.error(f"Failed to refresh token for user {self.user.username}")
                raise SpotifyTokenExpiredError(
                    "Failed to refresh Spotify access token. Please reconnect your Spotify account."
                )

    def _headers(self):
        """
        Return authorization headers for API requests.

        Returns:
            dict: Headers with Bearer token
        """
        self._ensure_valid_token()
        return {
            "Authorization": f"Bearer {self.account.access_token}",
            "Content-Type": "application/json",
        }

    def _handle_response_error(self, response, endpoint, method):
        """
        Handle HTTP error responses from Spotify API.

        Args:
            response: requests.Response object
            endpoint: str, the API endpoint being called
            method: str, HTTP method (GET, POST, etc)

        Raises:
            SpotifyTokenExpiredError: If token is revoked (401)
            SpotifyRateLimitError: If rate limited and retries exhausted (429)
            SpotifyAPIError: For other API errors
        """
        status_code = response.status_code

        try:
            error_data = response.json()
        except:
            error_data = {"error": response.text}

        if status_code == 401:
            # Token is invalid or revoked
            logger.warning(
                f"Unauthorized (401) for user {self.user.username} on {method} {endpoint}"
            )
            logger.warning(f"Error details: {error_data}")
            # Clear the token to force re-authentication
            self.account.access_token = ""
            self.account.refresh_token = ""
            self.account.save()
            raise SpotifyTokenExpiredError(
                "Your Spotify token has been revoked or is invalid. Please reconnect your Spotify account."
            )

        elif status_code == 429:
            # Rate limited
            retry_after = response.headers.get("Retry-After")
            logger.warning(
                f"Rate limited (429) on {method} {endpoint}. Retry-After: {retry_after}"
            )
            raise SpotifyRateLimitError(
                f"Spotify API rate limit exceeded. Try again in {retry_after or 'a few'} seconds."
            )

        elif status_code == 404:
            logger.warning(f"Not found (404) on {method} {endpoint}")
            raise SpotifyAPIError(f"Spotify resource not found: {endpoint}")

        elif status_code >= 500:
            logger.error(f"Spotify server error ({status_code}) on {method} {endpoint}")
            raise SpotifyAPIError(
                f"Spotify API server error ({status_code}). Try again later."
            )

        else:
            logger.error(
                f"API error ({status_code}) on {method} {endpoint}: {error_data}"
            )
            raise SpotifyAPIError(
                f"Spotify API error ({status_code}): {error_data.get('error', {}).get('message', 'Unknown error')}"
            )

    def _make_request(self, method, endpoint, **kwargs):
        """
        Make an HTTP request to Spotify API with retry logic.

        Args:
            method: str, HTTP method (GET, POST, PUT, DELETE)
            endpoint: str, API endpoint path
            **kwargs: Additional arguments to pass to requests

        Returns:
            dict: JSON response from Spotify

        Raises:
            SpotifyAPIError: On various API errors
            SpotifyRateLimitError: If rate limited after retries
            SpotifyTokenExpiredError: If token is invalid
        """
        url = f"{self.BASE_URL}{endpoint}"
        kwargs.setdefault("timeout", self.REQUEST_TIMEOUT)

        retry_count = 0
        last_exception = None

        while retry_count < self.MAX_RETRIES:
            try:
                logger.debug(
                    f"Making {method} request to {endpoint} (attempt {retry_count + 1})"
                )
                headers = self._headers()

                response = requests.request(
                    method=method, url=url, headers=headers, **kwargs
                )

                # Check for HTTP errors
                if response.status_code >= 400:
                    self._handle_response_error(response, endpoint, method)

                logger.debug(f"{method} {endpoint} successful")
                return response.json() if response.text else {}

            except SpotifyTokenExpiredError:
                # Token errors are not retryable
                raise

            except SpotifyRateLimitError as e:
                # Rate limit - retry with backoff
                if retry_count < self.MAX_RETRIES - 1:
                    delay = self.INITIAL_RETRY_DELAY * (2**retry_count)
                    logger.warning(f"Rate limited, retrying in {delay}s...")
                    time.sleep(delay)
                    retry_count += 1
                    last_exception = e
                    continue
                else:
                    raise

            except (Timeout, ConnectionError) as e:
                # Network errors are retryable
                if retry_count < self.MAX_RETRIES - 1:
                    delay = self.INITIAL_RETRY_DELAY * (2**retry_count)
                    logger.warning(f"Connection error: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                    retry_count += 1
                    last_exception = e
                    continue
                else:
                    logger.error(
                        f"Connection failed after {self.MAX_RETRIES} attempts: {e}"
                    )
                    raise SpotifyAPIError(
                        f"Unable to connect to Spotify API after {self.MAX_RETRIES} attempts: {str(e)}"
                    )

            except RequestException as e:
                # Other request errors
                logger.error(f"Request error on {method} {endpoint}: {e}")
                raise SpotifyAPIError(f"Spotify API request failed: {str(e)}")

        # This shouldn't be reached, but just in case
        if last_exception:
            raise last_exception

    def get(self, endpoint, **kwargs):
        """Make a GET request to Spotify API."""
        return self._make_request("GET", endpoint, **kwargs)

    def post(self, endpoint, **kwargs):
        """Make a POST request to Spotify API."""
        return self._make_request("POST", endpoint, **kwargs)

    def put(self, endpoint, **kwargs):
        """Make a PUT request to Spotify API."""
        return self._make_request("PUT", endpoint, **kwargs)

    def delete(self, endpoint, **kwargs):
        """Make a DELETE request to Spotify API."""
        return self._make_request("DELETE", endpoint, **kwargs)

    def get_user_profile(self):
        """
        Get current user's Spotify profile.

        Returns:
            dict: User profile data
        """
        logger.info(f"Fetching Spotify profile for user {self.user.username}")
        return self.get("/me")

    def get_playlists(self, limit=50, offset=0):
        """
        Get user's playlists.

        Args:
            limit: Number of playlists per page (max 50)
            offset: Pagination offset

        Returns:
            dict: Paginated playlists data
        """
        logger.info(
            f"Fetching playlists for user {self.user.username} (limit={limit}, offset={offset})"
        )
        return self.get("/me/playlists", params={"limit": limit, "offset": offset})

    def get_playlist_tracks(self, playlist_id, limit=100, offset=0):
        """
        Get tracks from a specific playlist.

        Args:
            playlist_id: Spotify playlist ID
            limit: Number of tracks per page (max 100)
            offset: Pagination offset

        Returns:
            dict: Paginated tracks data
        """
        logger.info(
            f"Fetching tracks from playlist {playlist_id} (limit={limit}, offset={offset})"
        )
        return self.get(
            f"/playlists/{playlist_id}/tracks",
            params={"limit": limit, "offset": offset},
        )
