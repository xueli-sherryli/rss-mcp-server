import os
import requests
import logging
from dotenv import load_dotenv
from fastmcp import FastMCP
from typing import Optional, List, Union
import xml.etree.ElementTree as ET
import html
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# --- Google Reader API Client ---

class GoogleReaderClient:
    def __init__(self):
        self.email = os.getenv("GOOGLE_READER_EMAIL")
        self.password = os.getenv("GOOGLE_READER_PASSWD")
        self.base_url = os.getenv("GOOGLE_READER_BASE_URL")
        self.sid = None
        self.auth = None
        self.token = None

        if not all([self.email, self.password, self.base_url]):
            raise ValueError("Missing required environment variables: GOOGLE_READER_EMAIL, GOOGLE_READER_PASSWD, GOOGLE_READER_BASE_URL")

    def _login(self):
        """Logs in to the API to get SID and Auth tokens."""
        login_url = f"{self.base_url}/accounts/ClientLogin"
        params = {'Email': self.email, 'Passwd': self.password}
        try:
            response = requests.post(login_url, data=params)
            response.raise_for_status()
            data = response.text.strip().split('\n')
            self.sid = [line for line in data if line.startswith('SID=')][0].split('=')[1]
            self.auth = [line for line in data if line.startswith('Auth=')][0].split('=')[1]
            logging.info("Login successful.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Login failed: {e}")
            raise Exception(f"Login failed: {e}")
        except IndexError:
            logging.error(f"Failed to parse login response: {response.text}")
            raise Exception(f"Failed to parse login response: {response.text}")

    def _get_token(self):
        """Fetches the T token required for subsequent API calls."""
        if not self.auth:
            self._login()
        
        token_url = f"{self.base_url}/reader/api/0/token"
        headers = {'Authorization': f'GoogleLogin auth={self.auth}'}
        try:
            response = requests.get(token_url, headers=headers)
            response.raise_for_status()
            self.token = response.text.strip()
            logging.info("Token acquired.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to get token: {e}")
            raise Exception(f"Failed to get token: {e}")

    def ensure_authenticated(self):
        """Ensures that the client is authenticated and has a valid token."""
        if not self.token:
            self._get_token()

    def make_request(self, method, endpoint: Optional[str], use_api_0_path: bool = True, full_url: Optional[str] = None, **kwargs):
        """Makes an authenticated request to the API."""
        self.ensure_authenticated()

        if full_url:
            url = full_url
        elif endpoint:
            base = self.base_url.rstrip('/')
            if use_api_0_path:
                url = f"{base}/reader/api/0/{endpoint}"
            else:
                # Handle special endpoints like 'directory/search'
                url = f"{base}/reader/{endpoint}"
        else:
            raise ValueError("Either 'endpoint' or 'full_url' must be provided.")

        headers = kwargs.get("headers", {})
        headers['Authorization'] = f'GoogleLogin auth={self.auth}'
        
        cookies = kwargs.get("cookies", {})
        cookies['SID'] = self.sid
        
        params = kwargs.get("params", {})
        params['T'] = self.token
        params.setdefault('client', 'fastmcp-server')

        kwargs["headers"] = headers
        kwargs["cookies"] = cookies
        kwargs["params"] = params

        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            unescaped_text = html.unescape(response.text)
            content_type = response.headers.get('Content-Type', '')
            if 'json' in content_type:
                try:
                    return json.loads(unescaped_text)
                except json.JSONDecodeError as je:
                    logging.error(f"Failed to parse JSON response after unescaping: {je}")
                    return unescaped_text
            elif 'xml' in content_type:
                try:
                    return ET.fromstring(unescaped_text.encode('utf-8'))
                except ET.ParseError as pe:
                    logging.error(f"Failed to parse XML response: {pe}")
                    return unescaped_text
            return unescaped_text
        except requests.exceptions.RequestException as e:
            if e.response is not None and e.response.headers.get('X-Reader-Google-Bad-Token') == 'true':
                logging.warning("Token expired. Re-authenticating.")
                self._get_token()
                params['T'] = self.token
                kwargs["params"] = params
                response = requests.request(method, url, **kwargs)
                response.raise_for_status()
                unescaped_text = html.unescape(response.text)
                content_type = response.headers.get('Content-Type', '')
                if 'json' in content_type:
                    try:
                        return json.loads(unescaped_text)
                    except json.JSONDecodeError as je:
                        logging.error(f"Failed to parse JSON response after unescaping: {je}")
                        return unescaped_text
                elif 'xml' in content_type:
                    try:
                        return ET.fromstring(unescaped_text.encode('utf-8'))
                    except ET.ParseError as pe:
                        logging.error(f"Failed to parse XML response: {pe}")
                        return unescaped_text
                return unescaped_text
            
            logging.error(f"API request to {endpoint} failed: {e}")
            raise Exception(f"API request to {endpoint} failed: {e}")


# --- MCP Server Setup ---

mcp = FastMCP(
    name="FreshAPI & Google Reader API Server",
    instructions="An MCP server to interact with a Google Reader compatible API (like FreshRSS).",
    host="0.0.0.0",
    port=8000
    )

client = GoogleReaderClient()

@mcp.tool()
async def add_subscription(feed_url: str, folder: Optional[str] = None, title: Optional[str] = None):
    """
    Adds a new feed subscription.
    :param feed_url: The URL of the RSS feed to subscribe to.
    :param folder: The folder to add the subscription to.
    :param title: A custom title for the subscription.
    """
    data = {'ac': 'subscribe', 's': f"feed/{feed_url}"}
    if folder:
        data['a'] = f"user/-/label/{folder}"
    if title:
        data['t'] = title
    return client.make_request("POST", "subscription/edit", data=data)

@mcp.tool()
async def quick_add_subscription(feed_url: str):
    """
    Quickly adds a new feed subscription without extra details.
    :param feed_url: The URL of the RSS feed to quickly subscribe to.
    """
    data = {'quickadd': f"feed/{feed_url}"}
    return client.make_request("POST", "subscription/quickadd", data=data)

@mcp.tool()
async def get_subscription_list(output_format: str = "json"):
    """
    Retrieves the list of current subscriptions.
    :param output_format: The desired output format (json or xml).
    """
    params = {'output': output_format}
    return client.make_request("GET", "subscription/list", params=params)

@mcp.tool()
async def get_unread_count(output_format: str = "json"):
    """
    Gets the unread count for feeds and folders.
    :param output_format: The desired output format (json or xml).
    """
    params = {'output': output_format}
    return client.make_request("GET", "unread-count", params=params)

@mcp.tool()
async def get_user_info():
    """Retrieves information about the current user."""
    return client.make_request("GET", "user-info")

@mcp.tool()
async def delete_subscription(feed_ids: List[str]):
    """
    Deletes one or more feed subscriptions.
    :param feed_ids: A list of feed IDs to delete, e.g., ['feed/52', 'feed/53'].
    """
    data = {'ac': 'unsubscribe', 's': feed_ids}
    return client.make_request("POST", "subscription/edit", data=data)

@mcp.tool()
async def mark_feed_as_read(feed_url: str, timestamp: Union[int, str]):
    """
    Marks all items in a specific feed as read.
    :param feed_url: The URL of the feed to mark as read.
    :param timestamp: Timestamp to mark read time.
    """
    try:
        timestamp = int(timestamp)
    except (ValueError, TypeError):
        raise ValueError("Timestamp must be a valid integer.")
    data = {'s': f'feed/{feed_url}', 'ts': timestamp}
    return client.make_request("POST", "mark-all-as-read", data=data)


@mcp.tool()
async def mark_folder_as_read(folder_name: str, timestamp: Union[int, str]):
    """
    Marks all items in a specific folder as read.
    :param folder_name: The name of the folder to mark as read.
    :param timestamp: Timestamp to mark read time.
    """
    try:
        timestamp = int(timestamp)
    except (ValueError, TypeError):
        raise ValueError("Timestamp must be a valid integer.")
    data = {'t': folder_name, 'ts': timestamp}
    return client.make_request("POST", "mark-all-as-read", data=data)


@mcp.tool()
async def mark_article_as_read(entry_id: str, feed_url: Optional[str] = None, async_op: bool = True):
    """
    Marks a single article as read.
    :param entry_id: The ID of the entry to mark as read.
    :param feed_url: The URL of the feed the article belongs to (optional).
    :param async_op: Whether to perform the operation asynchronously.
    """
    data = {
        'ac': 'edit-tags',
        'i': entry_id,
        'a': 'user/-/state/com.google/read',
        'async': str(async_op).lower()
    }
    if feed_url:
        data['s'] = f'feed/{feed_url}'
    return client.make_request("POST", "edit-tag", data=data)


@mcp.tool()
async def mark_article_as_unread(entry_id: str, async_op: bool = True):
    """
    Marks a single article as unread.
    :param entry_id: The ID of the entry to mark as unread.
    :param async_op: Whether to perform the operation asynchronously.
    """
    data = {
        'ac': 'edit-tags',
        'i': entry_id,
        'r': 'user/-/state/com.google/read',
        'async': str(async_op).lower()
    }
    return client.make_request("POST", "edit-tag", data=data)


@mcp.tool()
async def mark_articles_as_read(entry_ids: List[str], async_op: bool = True):
    """
    Marks multiple articles as read.
    :param entry_ids: A list of entry IDs to mark as read.
    :param async_op: Whether to perform the operation asynchronously.
    """
    data = {
        'ac': 'edit-tags',
        'a': 'user/-/state/com.google/read',
        'i': entry_ids,
        'async': str(async_op).lower()
    }
    return client.make_request("POST", "edit-tag", data=data)

@mcp.tool()
async def create_folder(folder_name: str, feed_url: str):
    """
    Creates a new folder (tag) and associates a feed with it.
    A feed must be provided to create a folder.
    :param folder_name: The name of the folder to create.
    :param feed_url: The URL of a feed to associate with this folder.
    """
    data = {
        'ac': 'edit',
        'a': f'user/-/label/{folder_name}',
        's': f'feed/{feed_url}'
    }
    return client.make_request("POST", "edit-tag", data=data)


@mcp.tool()
async def share_article(entry_id: str, stream_id: str):
    """
    Marks a specific article as a shared item.
    :param entry_id: The ID of the entry to share.
    :param stream_id: The stream ID of the entry.
    """
    data = {
        'a': 'user/-/state/com.google/broadcast',
        'i': entry_id,
        's': stream_id,
        'async': 'true'
    }
    return client.make_request("POST", "edit-tag", data=data)


@mcp.tool()
async def add_tag_to_item(entry_id: str, tag_name: str, async_op: bool = True):
    """
    Adds a single tag to a specific article.
    :param entry_id: The ID of the article/entry to tag.
    :param tag_name: The name of the tag to add (e.g., 'important').
    :param async_op: Whether to perform the operation asynchronously. Recommended to be True.
    """
    data = {
        'i': entry_id,
        'a': f'user/-/label/{tag_name}',
        'async': str(async_op).lower()
    }
    return client.make_request("POST", "edit-tag", data=data)


@mcp.tool()
async def add_tags_to_item(entry_id: str, tag_names: List[str], async_op: bool = True):
    """
    Adds multiple tags to a specific article.
    :param entry_id: The ID of the article/entry to tag.
    :param tag_names: A list of tag names to add (e.g., ['important', 'work']).
    :param async_op: Whether to perform the operation asynchronously. Recommended to be True.
    """
    data = {
        'i': entry_id,
        'a': [f'user/-/label/{tag}' for tag in tag_names],
        'async': str(async_op).lower()
    }
    return client.make_request("POST", "edit-tag", data=data)


@mcp.tool()
async def delete_folder(folder_name: str):
    """
    Deletes a folder. This does not delete the feeds within the folder.
    :param folder_name: The name of the folder to delete.
    """
    data = {
        'ac': 'disable-tags',
        's': f'user/-/label/{folder_name}',
        't': folder_name
    }
    return client.make_request("POST", "disable-tag", data=data)


@mcp.tool()
async def remove_tag_from_item(entry_id: str, tag_name: str, async_op: bool = True):
    """
    Removes a specific tag from an article.
    :param entry_id: The ID of the article/entry.
    :param tag_name: The name of the tag to remove.
    :param async_op: Whether to perform the operation asynchronously.
    """
    data = {
        'r': f'user/-/label/{tag_name}',
        'i': entry_id,
        'async': str(async_op).lower()
    }
    return client.make_request("POST", "edit-tag", data=data)


@mcp.tool()
async def remove_tag_from_all_articles(tag_name: str):
    """
    Removes a tag from all articles that have it.
    :param tag_name: The name of the tag to remove from all articles.
    """
    data = {
        's': f'user/-/label/{tag_name}',
        't': tag_name
    }
    return client.make_request("POST", "disable-tag", data=data)


@mcp.tool()
async def move_subscription(feed_url: str, old_folder: str, new_folder: str):
    """
    Moves a subscription from one folder to another.
    :param feed_url: The URL of the feed to move.
    :param old_folder: The name of the current folder.
    :param new_folder: The name of the target folder.
    """
    data = {
        'ac': 'edit',
        's': f'feed/{feed_url}',
        'r': f'user/-/label/{old_folder}',
        'a': f'user/-/label/{new_folder}'
    }
    return client.make_request("POST", "subscription/edit", data=data)


@mcp.tool()
async def rename_subscription(feed_url: str, new_title: str):
    """
    Renames a subscription feed.
    :param feed_url: The URL of the feed to rename.
    :param new_title: The new title for the subscription.
    """
    data = {
        'ac': 'edit',
        's': f'feed/{feed_url}',
        't': new_title
    }
    return client.make_request("POST", "subscription/edit", data=data)


@mcp.tool()
async def cancel_article_sharing(entry_id: str, async_op: bool = True):
    """
    Cancels sharing for a specific article.
    :param entry_id: The ID of the entry to stop sharing.
    :param async_op: Whether to perform the operation asynchronously.
    """
    data = {
        'r': 'user/-/state/com.google/broadcast',
        'i': entry_id,
        'async': str(async_op).lower()
    }
    return client.make_request("POST", "edit-tag", data=data)


@mcp.tool()
async def set_tag_sharing(tag_name: str, is_public: bool):
    """
    Sets the sharing preference for a specific tag.
    :param tag_name: The name of the tag.
    :param is_public: Set to True to make the tag public, False for private.
    """
    data = {
        's': f'user/-/label/{tag_name}',
        't': tag_name,
        'pub': str(is_public).lower()
    }
    params = {'client': 'settings'}
    return client.make_request("POST", "tag/edit", data=data, params=params)


@mcp.tool()
async def get_all_entries(
    count: Union[int, str] = 20,
    sort_order: Optional[str] = None,
    newer_than: Optional[Union[int, str]] = None,
    older_than: Optional[Union[int, str]] = None,
    exclude_target: Optional[str] = None,
    continuation: Optional[str] = None,
    output_format: str = "json"
):
    """
    Gets all entries from the reading list.
    :param count: Max number of entries to return (up to 1000).
    :param sort_order: Sort order ('o' for old->new, 'n' for new->old).
    :param newer_than: Unix timestamp to get items newer than this.
    :param older_than: Unix timestamp to get items older than this.
    :param exclude_target: Label to exclude (e.g., 'user/-/state/com.google/read').
    :param continuation: Continuation string for pagination.
    :param output_format: The desired output format (json or xml).
    """
    try:
        count = int(count)
        if newer_than is not None:
            newer_than = int(newer_than)
        if older_than is not None:
            older_than = int(older_than)
    except (ValueError, TypeError):
        raise ValueError("count, newer_than, and older_than must be valid integers.")
    endpoint = "stream/contents/user/-/state/com.google/reading-list"
    params = {'output': output_format, 'n': count}
    if sort_order:
        params['r'] = sort_order
    if newer_than:
        params['t'] = newer_than
    if older_than:
        params['ot'] = older_than
    if exclude_target:
        params['xt'] = exclude_target
    if continuation:
        params['c'] = continuation
    return client.make_request("GET", endpoint, params=params)


@mcp.tool()
async def get_friend_list():
    """Retrieves the user's friend list."""
    return client.make_request("GET", "friend/list")


@mcp.tool()
async def get_preference_list():
    """Retrieves the user's preference list."""
    return client.make_request("GET", "preference/list")


@mcp.tool()
async def get_starred_articles(count: Union[int, str] = 20, output_format: str = "json"):
    """
    Retrieves a list of starred articles.
    :param count: The maximum number of starred articles to retrieve (max 1000).
    :param output_format: The desired output format (json or xml).
    """
    try:
        count = int(count)
    except (ValueError, TypeError):
        raise ValueError("count must be a valid integer.")
    endpoint = "stream/contents/user/-/state/com.google/starred"
    params = {'n': count, 'output': output_format}
    return client.make_request("GET", endpoint, params=params)


@mcp.tool()
async def parse_feed_url(feed_url: str, count: Union[int, str] = 20, exclude_target: Optional[str] = None):
    """
    Parses a feed URL to retrieve its entries.
    :param feed_url: The URL of the feed to parse.
    :param count: Number of entries to load.
    :param exclude_target: Label to exclude from the results.
    """
    try:
        count = int(count)
    except (ValueError, TypeError):
        raise ValueError("count must be a valid integer.")
    # For this special case, we construct the full URL manually to avoid issues with
    # the requests library parsing a URL within the path.
    base = client.base_url.rstrip('/')
    full_url = f"{base}/reader/api/0/atom/feed/{feed_url}"
    
    params = {'n': count}
    if exclude_target:
        params['xt'] = exclude_target
        
    return client.make_request("GET", endpoint=None, full_url=full_url, params=params)


@mcp.tool()
async def freshapi_get_stream_item_ids(
    stream_id: str,
    count: Union[int, str] = 20,
    sort_order: Optional[str] = None,
    continuation: Optional[str] = None,
    exclude_target: Optional[str] = None,
    start_time: Optional[Union[int, str]] = None,
    stop_time: Optional[Union[int, str]] = None,
    filter_target: Optional[str] = None
):
    """
    (freshapi-specific) Fetches a list of item IDs from a stream (feed/folder).
    :param stream_id: The ID of the stream (e.g., 'feed/5', 'user/-/label/News').
    :param count: The maximum number of item IDs to return.
    :param sort_order: Sort order ('o' for old->new, 'd' for new->old).
    :param continuation: Continuation string for pagination.
    :param exclude_target: Label to exclude from the results.
    :param start_time: The time from which you want to retrieve items (Unix timestamp).
    :param stop_time: The time until which you want to retrieve items (Unix timestamp).
    :param filter_target: Label to include in the results.
    """
    try:
        count = int(count)
        if start_time is not None:
            start_time = int(start_time)
        if stop_time is not None:
            stop_time = int(stop_time)
    except (ValueError, TypeError):
        raise ValueError("count, start_time, and stop_time must be valid integers.")
    endpoint = "stream/items/ids"
    params = {'s': stream_id, 'n': count}
    if sort_order:
        params['r'] = sort_order
    if continuation:
        params['c'] = continuation
    if exclude_target:
        params['xt'] = exclude_target
    if start_time:
        params['ot'] = start_time
    if stop_time:
        params['nt'] = stop_time
    if filter_target:
        params['it'] = filter_target
    return client.make_request("GET", endpoint, params=params)


@mcp.tool()
async def freshapi_get_stream_item_contents(item_ids: List[str]):
    """
    (freshapi-specific) Retrieves the full content for a list of item IDs.
    :param item_ids: A list of item IDs to fetch content for.
    """
    endpoint = "stream/items/contents"
    data = {'i': item_ids}
    return client.make_request("POST", endpoint, data=data)


@mcp.tool()
async def get_shared_entries(count: Union[int, str] = 20):
    """
    Retrieves the user's shared entries.
    :param count: The number of shared articles to retrieve.
    """
    try:
        count = int(count)
    except (ValueError, TypeError):
        raise ValueError("count must be a valid integer.")
    endpoint = "reader/atom/user/-/state/com.google/broadcast"
    params = {'n': count}
    return client.make_request("GET", endpoint, params=params)


@mcp.tool()
async def get_tag_list(output_format: str = "json"):
    """
    Retrieves a list of all tags (which includes folders).
    :param output_format: The desired output format (json or xml).
    """
    params = {'output': output_format}
    return client.make_request("GET", "tag/list", params=params)


@mcp.tool()
async def search_greader_categories(search_term: str):
    """
    Searches GReader categories. Note: This returns an HTML page.
    :param search_term: The keyword to search for.
    """
    params = {'q': search_term}
    return client.make_request("GET", "directory/search", use_api_0_path=False, params=params)


@mcp.tool()
async def search_item_ids(search_term: str, output_format: str = "json"):
    """
    Searches for item IDs that match a given term.
    :param search_term: The keyword to search for.
    :param output_format: The desired output format (json or xml).
    """
    params = {'q': search_term, 'output': output_format}
    return client.make_request("GET", "search/items/ids", params=params)


@mcp.tool()
async def get_item_contents(item_ids: List[str], output_format: str = "json"):
    """
    Retrieves the contents of specific items by their IDs.
    :param item_ids: A list of item IDs to retrieve content for.
    :param output_format: The desired output format (json or atom).
    """
    data = {'i': item_ids}
    params = {'output': output_format}
    return client.make_request("POST", "stream/items/contents", data=data, params=params)


if __name__ == "__main__":
    mcp.run(transport='sse')
